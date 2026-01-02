import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
import inspect
import re
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator

import os
from fastapi import BackgroundTasks, FastAPI, HTTPException, Response, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import select

from datapub.db.base import SessionLocal
from datetime import datetime
from datapub.db.models import Document, Orgao, State, Municipality, DocumentType, ChatSession, ChatMessage
from datapub.db.init_db import init_db as init_db_sync
from datapub.etl.normalize import run_normalize
from datapub.etl.ibge_localidades import run_sync_ibge

# Local imports
from datapub import cli as datapub_cli
from datapub.rag.ingest import run_ingest
from datapub.rag.prune import run_prune
import cognee
from datapub.api.homepage import HomePage


app = FastAPI(title="DataPub API", version="0.1.0")

# --------- CORS (for external Swagger UI and web clients) ---------
# Allow origins can be configured via env var CORS_ALLOWED_ORIGINS
# Default includes Swagger UI container on localhost:8080
_cors_env = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080")
_allowed_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------- API Metrics ---------
API_REQUESTS = Counter(
    "datapub_api_requests_total",
    "Total de requisições HTTP da API",
    labelnames=("method", "path", "status_code"),
)
API_LATENCY = Histogram(
    "datapub_api_request_duration_seconds",
    "Duração das requisições HTTP",
    labelnames=("method", "path"),
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    path = request.url.path
    method = request.method
    status = str(response.status_code)
    try:
        API_REQUESTS.labels(method=method, path=path, status_code=status).inc()
        API_LATENCY.labels(method=method, path=path).observe(duration)
    except Exception:
        # Safety: never break requests due to metrics errors
        pass
    return response


# --------- Models ---------
class ChatQuery(BaseModel):
    query: str = Field(..., description="Texto da consulta", example="licitações saúde")
    estado: Optional[str] = Field(None, description="UF do estado, ex: PA", example="PA")
    municipio: Optional[str] = Field(None, example="Belém")
    orgao: Optional[str] = Field(None, description="Órgão público, ex: ALEPA", example="ALEPA")
    entity: Optional[str] = Field(None, description="Identificador interno, ex: al_pa", example="al_pa")


class ChatSessionCreate(BaseModel):
    title: Optional[str] = Field(None, example="meu chat")
    estado: Optional[str] = Field(None, example="PA")
    municipio: Optional[str] = Field(None, example="Belém")
    orgao: Optional[str] = Field(None, example="ALEPA")
    entity: Optional[str] = Field(None, example="al_pa")


class ChatSessionOut(BaseModel):
    id: int
    title: Optional[str]
    created_at: str
    filters: Dict[str, Optional[str]]


class ChatMessageIn(BaseModel):
    query: str = Field(..., example="licitações saúde")
    # Optional per-call override; otherwise use default
    history_limit: Optional[int] = Field(None, example=10)


class ChatSessionUpdate(BaseModel):
    title: Optional[str] = Field(None, example="meu chat renomeado")
    entity: Optional[str] = Field(None, example="al_pa")
    estado: Optional[str] = Field(None, example="PA")
    municipio: Optional[str] = Field(None, example="Belém")
    orgao: Optional[str] = Field(None, example="ALEPA")


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class TriggerExtractor(BaseModel):
    entity: str = Field(..., description="ex: al_pa, al_ms, al_go, al_ce, al_ac")
    tipo: str = Field("diario", description="tipo de extractor, ex: diario")
    start: Optional[str] = Field(None, description="YYYY-MM-DD")
    end: Optional[str] = Field(None, description="YYYY-MM-DD")
    headless: Optional[bool] = Field(True, description="Executar navegador em modo headless")


class TriggerProcessor(BaseModel):
    entity: str = Field(..., description="ex: al_pa")
    tipo: str = Field("diario", description="tipo de processamento, ex: diario")
    start: Optional[str] = Field(None, description="YYYY-MM-DD")
    end: Optional[str] = Field(None, description="YYYY-MM-DD")


class IngestBody(BaseModel):
    entity: str
    file: Optional[str] = Field(None, description="Nome do arquivo em storage/processed/<entity>")
    all: bool = Field(False, description="Ingerir todos os arquivos processados da entidade")


# Single shared threadpool for blocking tasks
executor = ThreadPoolExecutor(max_workers=4)


def _resolve_class(mapping: List[Dict[str, type]], tipo: str):
    for class_dict in mapping:
        if tipo in class_dict:
            return class_dict[tipo]
    return None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/health/config", tags=["Chat"], summary="Exibe configurações relevantes do chat")
async def health_config():
    # Resolve Cognee version safely
    cognee_version = None
    try:
        try:
            from importlib import metadata as importlib_metadata  # Python 3.8+
        except Exception:  # pragma: no cover - unlikely
            import importlib_metadata  # type: ignore
        try:
            cognee_version = importlib_metadata.version("cognee")
        except Exception:
            cognee_version = getattr(cognee, "__version__", None)
    except Exception:
        cognee_version = None

    # Database info (non-destructive, best-effort)
    from datapub.db.base import engine as db_engine
    db_info = {
        "url": None,
        "dialect": None,
        "server_version": None,
        "alembic_current_revision": None,
        "migrations": None,
    }
    try:
        url_obj = db_engine.url
        db_info["url"] = {
            "drivername": url_obj.drivername,
            "database": url_obj.database,
            "username": bool(url_obj.username),
            "host": url_obj.host,
            "port": url_obj.port,
        }
        db_info["dialect"] = db_engine.dialect.name
        with db_engine.connect() as conn:
            try:
                res = conn.execute("SELECT version_num FROM alembic_version")
                row = res.first()
                if row:
                    db_info["alembic_current_revision"] = row[0]
            except Exception:
                db_info["alembic_current_revision"] = None
            # server version (best effort)
            try:
                sv = getattr(conn.dialect, "server_version_info", None)
                if sv:
                    db_info["server_version"] = ".".join(str(x) for x in sv if x is not None)
            except Exception:
                pass
    except Exception:
        pass

    # Migrations info from filesystem
    try:
        versions_dir = Path(__file__).resolve().parents[1] / "migrations" / "versions"
        if versions_dir.exists():
            files = sorted([p.name for p in versions_dir.glob("*.py") if p.is_file()])
            latest_file = files[-1] if files else None
            latest_revision = None
            if latest_file:
                try:
                    src = (versions_dir / latest_file).read_text(encoding="utf-8", errors="ignore")
                    import re as _re
                    m = _re.search(r"^revision\s*=\s*['\"]([^'\"]+)['\"]", src, flags=_re.M)
                    if m:
                        latest_revision = m.group(1)
                except Exception:
                    latest_revision = None
            current_rev = db_info.get("alembic_current_revision")
            pending = None
            if latest_revision:
                pending = (current_rev != latest_revision)
            db_info["migrations"] = {
                "path": str(versions_dir),
                "count": len(files),
                "latest": latest_file,
                "latest_revision": latest_revision,
                "current_revision": current_rev,
                "pending": pending,
            }
    except Exception:
        pass

    return {
        "chat_history_limit": _get_int_env("CHAT_HISTORY_LIMIT", 10),
        "chat_retention_messages": _get_int_env("CHAT_RETENTION_MESSAGES", 0),
        "api_keys_configured": bool(_get_configured_api_keys()),
        "api_version": app.version,
        "cognee_version": cognee_version,
        "db": db_info,
        "neo4j_url": os.getenv("NEO4J_URL", None),
    }


@app.get("/health/db", tags=["Health"], summary="Ping de conexão ao banco da aplicação")
async def health_db():
    from datapub.db.base import engine as db_engine
    info = {"ok": False, "dialect": db_engine.dialect.name, "error": None}
    try:
        with db_engine.connect() as conn:
            try:
                conn.execute("SELECT 1")
            except Exception:
                pass
        info["ok"] = True
    except Exception as e:
        info["error"] = str(e)
    return info


@app.get("/scheduler/info", tags=["Scheduler"], summary="Exibe variáveis do agendador (compose)")
async def scheduler_info():
    return {
        "cron_pipeline": os.getenv("CRON_PIPELINE", "0 3 * * *"),
        "entities": os.getenv("ENTITIES", ""),
        "start": os.getenv("START", None),
        "end": os.getenv("END", None),
    }


@app.get("/health/neo4j", tags=["Health"], summary="Ping TCP ao serviço Neo4j (bolt)")
async def health_neo4j():
    import socket
    from urllib.parse import urlparse

    url = os.getenv("NEO4J_URL", "")
    out = {"ok": False, "url": url or None, "host": None, "port": None, "error": None}
    if not url:
        out["error"] = "NEO4J_URL not configured"
        return out
    try:
        p = urlparse(url)
        host = p.hostname or "neo4j"
        port = p.port or 7687
        out["host"], out["port"] = host, port
        with socket.create_connection((host, port), timeout=1.5):
            out["ok"] = True
    except Exception as e:
        out["error"] = str(e)
    return out


@app.get("/health/swagger", tags=["Health"], summary="Ping TCP ao Swagger UI (container)")
async def health_swagger():
    import socket
    host, port = "swagger-ui", 8080
    out = {"ok": False, "host": host, "port": port, "error": None}
    try:
        with socket.create_connection((host, port), timeout=1.5):
            out["ok"] = True
    except Exception as e:
        out["error"] = str(e)
    return out


@app.get("/health/prometheus", tags=["Health"], summary="Ping TCP ao Prometheus (container)")
async def health_prometheus():
    import socket
    host, port = "prometheus", 9090
    out = {"ok": False, "host": host, "port": port, "error": None}
    try:
        with socket.create_connection((host, port), timeout=1.5):
            out["ok"] = True
    except Exception as e:
        out["error"] = str(e)
    return out


@app.get("/health/pgadmin", tags=["Health"], summary="Ping TCP ao pgAdmin (container)")
async def health_pgadmin():
    import socket
    host, port = "pgadmin", 5050
    out = {"ok": False, "host": host, "port": port, "error": None}
    try:
        with socket.create_connection((host, port), timeout=1.5):
            out["ok"] = True
    except Exception as e:
        out["error"] = str(e)
    return out


@app.get("/", include_in_schema=False)
async def landing() -> HTMLResponse:
    # Delegado para a classe HomePage (mantém compatibilidade atual)
    base = os.getenv("PUBLIC_BASE_URL", "http://localhost")
    try:
        from datapub.db.base import engine as _engine
        _url = _engine.url
        _dialect = _engine.dialect.name
        _db_name = _url.database or ""
        _host = _url.host or ""
        _port = _url.port or ""
        if _dialect.startswith("sqlite"):
            db_target = _db_name or ":memory:"
        else:
            db_target = f"{_db_name} @ {_host}:{_port}".strip()
        db_overview = {"dialect": _dialect, "target": db_target}
    except Exception:
        db_overview = {"dialect": "desconhecido", "target": "indisponível"}

    neo4j_url = os.getenv("NEO4J_URL", None) or "não configurado"
    html = HomePage.render(base, db_overview, neo4j_url)
    return HTMLResponse(content=html, status_code=200)

@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# --------- DB Dependency ---------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --------- Pagination helpers ---------
def set_pagination_headers(request: Request, response: Response, limit: int, offset: int, total: int):
    response.headers["X-Total-Count"] = str(total)

    def with_params(o: int):
        return str(request.url.include_query_params(limit=limit, offset=o))

    links = []
    if offset + limit < total:
        links.append(f'<{with_params(offset + limit)}>; rel="next"')
    if offset > 0:
        prev = max(0, offset - limit)
        links.append(f'<{with_params(prev)}>; rel="prev"')
    links.append(f'<{with_params(0)}>; rel="first"')
    last_offset = (max(total - 1, 0) // max(limit, 1)) * max(limit, 1)
    links.append(f'<{with_params(last_offset)}>; rel="last"')
    response.headers["Link"] = ", ".join(links)


# --------- Document Listing ---------
class DocumentOut(BaseModel):
    id: int
    titulo: str
    url: Optional[str]
    data_publicacao: Optional[str]
    descricao: Optional[str]
    orgao_nome: Optional[str]
    orgao_tipo: Optional[str]
    orgao_estado: Optional[str]
    orgao_cidade: Optional[str]
    tipo_documento_nome: Optional[str]


@app.get("/documents", response_model=List[DocumentOut])
async def list_documents(
    estado: Optional[str] = None,
    municipio: Optional[str] = None,
    orgao: Optional[str] = None,
    tipo: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db=Depends(get_db), request: Request = None, response: Response = None,
):
    query = db.query(Document, Orgao, State, Municipality, DocumentType).\
        outerjoin(Orgao, Document.orgao_id == Orgao.id).\
        outerjoin(State, Document.state_id == State.id).\
        outerjoin(Municipality, Document.municipality_id == Municipality.id).\
        outerjoin(DocumentType, Document.document_type_id == DocumentType.id)

    if estado:
        query = query.filter(State.uf == estado.upper())
    if municipio:
        query = query.filter(Municipality.name.ilike(f"%{municipio}%"))
    if orgao:
        query = query.filter(Orgao.name.ilike(f"%{orgao}%"))
    if tipo:
        query = query.filter(DocumentType.name.ilike(f"%{tipo}%"))
    if q:
        # Basic text search on title/description
        query = query.filter(
            (Document.title.ilike(f"%{q}%")) | (Document.description.ilike(f"%{q}%"))
        )

    total = query.count()
    rows = query.order_by(Document.publication_date.desc().nullslast(), Document.id.desc()).limit(limit).offset(offset).all()

    results: List[DocumentOut] = []
    for d, o, s, m, t in rows:
        results.append(
            DocumentOut(
                id=d.id,
                titulo=d.title,
                url=d.url,
                data_publicacao=d.publication_date.isoformat() if d.publication_date else None,
                descricao=d.description,
                orgao_nome=o.name if o else None,
                orgao_tipo=o.tipo if o else None,
                orgao_estado=s.name if s else None,
                orgao_cidade=m.name if m else None,
                tipo_documento_nome=t.name if t else None,
            )
        )
    if request is not None and response is not None:
        set_pagination_headers(request, response, limit, offset, total)
    return results


# --------- Admin/ETL ---------
@app.post("/admin/init-db")
async def admin_init_db():
    try:
        init_db_sync()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ETLRequest(BaseModel):
    entity: Optional[str] = None


@app.post("/etl/run")
async def etl_run(payload: ETLRequest, background: BackgroundTasks):
    def _run(entity):
        run_normalize(entity)

    background.add_task(executor.submit, _run, payload.entity)
    return {"status": "scheduled", "entity": payload.entity}


@app.post("/admin/sync-ibge")
async def admin_sync_ibge(background: BackgroundTasks):
    def _run():
        attempts = 0
        last_err = None
        while attempts < 3:
            try:
                run_sync_ibge()
                return
            except Exception as e:
                last_err = e
                time.sleep(2 * (attempts + 1))
                attempts += 1
        raise last_err

    background.add_task(executor.submit, _run)
    return {"status": "scheduled", "task": "sync-ibge"}


@app.get("/entities")
async def entities():
    return {
        "extractors": {
            k: list(d.keys()) if isinstance(d, dict) else [list(x.keys())[0] for x in d]
            for k, d in datapub_cli.extractors.items()
        },
        "processors": {
            k: list(d.keys()) if isinstance(d, dict) else [list(x.keys())[0] for x in d]
            for k, d in datapub_cli.processors.items()
        },
    }


@app.post("/chat/search", tags=["Chat"], summary="Busca rápida com filtros (sem sessão)")
async def chat_search(payload: ChatQuery):
    filters = []
    if payload.entity:
        filters.append(f"entidade:{payload.entity}")
    if payload.estado:
        filters.append(f"estado:{payload.estado}")
    if payload.municipio:
        filters.append(f"municipio:{payload.municipio}")
    if payload.orgao:
        filters.append(f"orgao:{payload.orgao}")

    query_text = payload.query
    if filters:
        query_text = f"{payload.query}\n\nContexto/Restrições: {', '.join(filters)}"

    # Build structured metadata/context for Cognee when supported
    meta = {
        "entity": payload.entity,
        "estado": payload.estado,
        "municipio": payload.municipio,
        "orgao": payload.orgao,
    }
    ctx = {"filters": filters}
    try:
        results = await _cognee_search(query_text=query_text, context=ctx, metadata=meta)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar Cognee: {e}")

    return {
        "query": payload.query,
        "filters": filters,
        "results": results,
    }


# --------- Chat with History ---------
def _compose_filters(entity: Optional[str], estado: Optional[str], municipio: Optional[str], orgao: Optional[str]) -> List[str]:
    filters: List[str] = []
    if entity:
        filters.append(f"entidade:{entity}")
    if estado:
        filters.append(f"estado:{estado}")
    if municipio:
        filters.append(f"municipio:{municipio}")
    if orgao:
        filters.append(f"orgao:{orgao}")
    return filters


def _apply_filters_to_query(query: str, filters: List[str]) -> str:
    if not filters:
        return query
    return f"{query}\n\nContexto/Restrições: {', '.join(filters)}"


def _get_last_messages(db, session_id: int, limit: int) -> List[ChatMessage]:
    q = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(limit)
    )
    rows = list(q.all())
    rows.reverse()  # chronological order
    return rows


def _history_as_text(messages: List[ChatMessage]) -> str:
    if not messages:
        return ""
    lines: List[str] = ["Histórico de conversa (recente primeiro):"]
    for m in messages[-10:]:  # cap snippet in text; final limit controlled separately
        role = m.role
        content = (m.content or "").strip()
        if not content:
            continue
        lines.append(f"- {role}: {content}")
    return "\n".join(lines)


@app.post(
    
    "/chat/sessions",
    response_model=ChatSessionOut,
    tags=["Chat"],
    summary="Cria uma sessão de chat",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "default": {
                            "summary": "Sessão criada",
                            "value": {
                                "id": 1,
                                "title": "meu chat",
                                "created_at": "2025-09-20T12:34:56Z",
                                "filters": {"entity": "al_pa", "estado": "PA", "municipio": "Belém", "orgao": "ALEPA"},
                            },
                        }
                    }
                }
            }
        }
    },
)
async def create_chat_session(body: ChatSessionCreate, db=Depends(get_db)):
    sess = ChatSession(
        title=body.title,
        entity=(body.entity or None),
        estado=(body.estado or None),
        municipio=(body.municipio or None),
        orgao=(body.orgao or None),
    )
    db.add(sess)
    db.commit()
    db.refresh(sess)
    return ChatSessionOut(
        id=sess.id,
        title=sess.title,
        created_at=sess.created_at.isoformat(),
        filters={
            "entity": sess.entity,
            "estado": sess.estado,
            "municipio": sess.municipio,
            "orgao": sess.orgao,
        },
    )


@app.get(
    "/chat/sessions",
    response_model=List[ChatSessionOut],
    tags=["Chat"],
    summary="Lista sessões de chat",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "default": {
                            "summary": "Lista de sessões",
                            "value": [
                                {
                                    "id": 1,
                                    "title": "meu chat",
                                    "created_at": "2025-09-20T12:34:56Z",
                                    "filters": {"entity": "al_pa", "estado": "PA", "municipio": "Belém", "orgao": "ALEPA"},
                                }
                            ],
                        }
                    }
                }
            }
        }
    },
)
async def list_chat_sessions(limit: int = 50, offset: int = 0, db=Depends(get_db)):
    q = db.query(ChatSession).order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
    rows = q.limit(limit).offset(offset).all()
    return [
        ChatSessionOut(
            id=s.id,
            title=s.title,
            created_at=s.created_at.isoformat(),
            filters={"entity": s.entity, "estado": s.estado, "municipio": s.municipio, "orgao": s.orgao},
        )
        for s in rows
    ]


@app.get(
    "/chat/sessions/{session_id}",
    response_model=ChatSessionOut,
    tags=["Chat"],
    summary="Obtém uma sessão",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "default": {
                            "summary": "Sessão",
                            "value": {
                                "id": 1,
                                "title": "meu chat",
                                "created_at": "2025-09-20T12:34:56Z",
                                "filters": {"entity": "al_pa", "estado": "PA", "municipio": "Belém", "orgao": "ALEPA"},
                            },
                        }
                    }
                }
            }
        }
    },
)
async def get_chat_session(session_id: int, db=Depends(get_db)):
    s = db.query(ChatSession).get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    return ChatSessionOut(
        id=s.id,
        title=s.title,
        created_at=s.created_at.isoformat(),
        filters={"entity": s.entity, "estado": s.estado, "municipio": s.municipio, "orgao": s.orgao},
    )


@app.get(
    "/chat/sessions/{session_id}/messages",
    response_model=List[ChatMessageOut],
    tags=["Chat"],
    summary="Lista mensagens da sessão",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "default": {
                            "summary": "Mensagens",
                            "value": [
                                {"id": 1, "role": "user", "content": "licitações saúde", "created_at": "2025-09-20T12:35:00Z"},
                                {"id": 2, "role": "assistant", "content": "1. Doc 1 — http://x/1", "created_at": "2025-09-20T12:35:01Z"},
                            ],
                        }
                    }
                }
            }
        }
    },
)
async def list_chat_messages(session_id: int, limit: int = 50, offset: int = 0, db=Depends(get_db)):
    if not db.query(ChatSession).get(session_id):
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    q = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    rows = q.limit(limit).offset(offset).all()
    return [
        ChatMessageOut(id=m.id, role=m.role, content=m.content, created_at=m.created_at.isoformat())
        for m in rows
    ]


def _format_results_as_text(results: List[Dict]) -> str:
    lines: List[str] = []
    for i, r in enumerate(results[:5], start=1):
        title = r.get("title") or r.get("titulo") or r.get("text") or r.get("content") or "resultado"
        url = r.get("url") or r.get("link")
        if url:
            lines.append(f"{i}. {title} — {url}")
        else:
            lines.append(f"{i}. {title}")
    if not lines:
        lines = ["Nenhum resultado encontrado."]
    return "\n".join(lines)


@app.post(
    "/chat/sessions/{session_id}/query",
    response_model=Dict[str, object],
    tags=["Chat"],
    summary="Pergunta síncrona na sessão",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "default": {
                            "summary": "Resposta com resultados",
                            "value": {
                                "session_id": 1,
                                "filters": ["entidade:al_pa", "estado:PA"],
                                "history_used": 10,
                                "query": "licitações saúde",
                                "results": [{"title": "Doc 1", "url": "http://x/1"}],
                                "assistant": "1. Doc 1 — http://x/1",
                            },
                        }
                    }
                }
            }
        }
    },
)
async def chat_query_session(session_id: int, body: ChatMessageIn, db=Depends(get_db)):
    s = db.query(ChatSession).get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    # Persist user message
    user_msg = ChatMessage(session_id=s.id, role="user", content=body.query)
    db.add(user_msg)
    db.flush()

    # Build query with session filters and recent history
    filters = _compose_filters(s.entity, s.estado, s.municipio, s.orgao)
    history_limit = max(0, int(body.history_limit) if body.history_limit is not None else int(os.getenv("CHAT_HISTORY_LIMIT", "10")))
    history_msgs = _get_last_messages(db, s.id, history_limit + 1)  # includes current user message
    history_text = _history_as_text(history_msgs[:-1])  # prior messages only
    query_text = body.query
    if history_text:
        query_text = f"{history_text}\n\nPergunta atual: {query_text}"
    query_text = _apply_filters_to_query(query_text, filters)

    # Structured context
    ctx = {
        "session_id": s.id,
        "filters": filters,
        "history": [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in history_msgs[:-1]],
    }
    meta = {"entity": s.entity, "estado": s.estado, "municipio": s.municipio, "orgao": s.orgao}
    try:
        results = await _cognee_search(query_text=query_text, context=ctx, metadata=meta)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao consultar Cognee: {e}")

    # Prepare assistant content (simple textual summary of results)
    assistant_text = _format_results_as_text(results)

    # Persist assistant message
    asst_msg = ChatMessage(session_id=s.id, role="assistant", content=assistant_text)
    db.add(asst_msg)
    # Touch session updated_at
    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    # Retention policy (optional)
    _enforce_retention(db, s.id)

    return {
        "session_id": s.id,
        "filters": filters,
        "history_used": history_limit,
        "query": body.query,
        "results": results,
        "assistant": assistant_text,
    }


@app.post(
    "/chat/sessions/{session_id}/stream",
    tags=["Chat"],
    summary="Pergunta com resposta em streaming (SSE)",
    responses={
        200: {
            "content": {
                "text/event-stream": {
                    "examples": {
                        "sse": {
                            "summary": "Fluxo SSE",
                            "value": """
data: {\"type\": \"start\", \"session_id\": 1, \"filters\": [\"entidade:al_pa\"], \"history_used\": 10}

data: {\"type\": \"chunk\", \"content\": \"1. Doc 1 — http://x/1\"}

data: {\"type\": \"end\"}
""",
                        }
                    }
                }
            }
        }
    },
)
async def chat_stream_session(session_id: int, body: ChatMessageIn, db=Depends(get_db)):
    s = db.query(ChatSession).get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    # Persist user message early
    user_msg = ChatMessage(session_id=s.id, role="user", content=body.query)
    db.add(user_msg)
    db.flush()

    filters = _compose_filters(s.entity, s.estado, s.municipio, s.orgao)
    history_limit = max(0, int(body.history_limit) if body.history_limit is not None else int(os.getenv("CHAT_HISTORY_LIMIT", "10")))
    history_msgs = _get_last_messages(db, s.id, history_limit + 1)
    history_text = _history_as_text(history_msgs[:-1])
    query_text = body.query
    if history_text:
        query_text = f"{history_text}\n\nPergunta atual: {query_text}"
    query_text = _apply_filters_to_query(query_text, filters)

    ctx = {
        "session_id": s.id,
        "filters": filters,
        "history": [{"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()} for m in history_msgs[:-1]],
    }
    meta = {"entity": s.entity, "estado": s.estado, "municipio": s.municipio, "orgao": s.orgao}
    try:
        results = await _cognee_search(query_text=query_text, context=ctx, metadata=meta)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao consultar Cognee: {e}")

    assistant_text = _format_results_as_text(results)

    # Persist assistant full message (even though we stream chunks)
    asst_msg = ChatMessage(session_id=s.id, role="assistant", content=assistant_text)
    db.add(asst_msg)
    s.updated_at = datetime.utcnow()
    db.commit()
    # Retention policy
    _enforce_retention(db, s.id)

    async def event_gen() -> AsyncGenerator[bytes, None]:
        # Basic SSE stream with prelude, chunks, and end
        pre = {"type": "start", "session_id": s.id, "filters": filters, "history_used": history_limit}
        yield f"data: {json.dumps(pre, ensure_ascii=False)}\n\n".encode("utf-8")

        chunk_size = 80
        for i in range(0, len(assistant_text), chunk_size):
            part = assistant_text[i:i+chunk_size]
            payload = {"type": "chunk", "content": part}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")
            await asyncio.sleep(0)  # allow event loop to switch

        end = {"type": "end"}
        yield f"data: {json.dumps(end)}\n\n".encode("utf-8")

    return Response(event_gen(), media_type="text/event-stream")


@app.delete(
    "/chat/sessions/{session_id}",
    tags=["Chat"],
    summary="Apaga sessão de chat",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "default": {
                            "summary": "Sessão apagada",
                            "value": {"status": "deleted", "session_id": 1},
                        }
                    }
                }
            }
        }
    },
)
async def delete_chat_session(session_id: int, db=Depends(get_db)):
    s = db.query(ChatSession).get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    db.delete(s)
    db.commit()
    return {"status": "deleted", "session_id": session_id}


@app.delete(
    "/chat/sessions/{session_id}/messages",
    tags=["Chat"],
    summary="Limpa mensagens da sessão",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "default": {
                            "summary": "Mensagens limpas",
                            "value": {"status": "cleared", "session_id": 1, "deleted": 2},
                        }
                    }
                }
            }
        }
    },
)
async def clear_chat_messages(session_id: int, db=Depends(get_db)):
    s = db.query(ChatSession).get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    # delete in bulk
    count = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete(synchronize_session=False)
    s.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "cleared", "session_id": session_id, "deleted": count}


@app.patch(
    "/chat/sessions/{session_id}",
    response_model=ChatSessionOut,
    tags=["Chat"],
    summary="Renomeia sessão de chat",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "default": {
                            "summary": "Sessão renomeada",
                            "value": {
                                "id": 1,
                                "title": "novo título",
                                "created_at": "2025-09-20T12:34:56Z",
                                "filters": {"entity": "al_pa", "estado": "PA", "municipio": "Belém", "orgao": "ALEPA"},
                            },
                        }
                    }
                }
            }
        }
    },
)
async def rename_chat_session(session_id: int, body: ChatSessionUpdate, db=Depends(get_db)):
    s = db.query(ChatSession).get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    if body.title is not None:
        s.title = body.title
    if body.entity is not None:
        s.entity = body.entity or None
    if body.estado is not None:
        s.estado = body.estado or None
    if body.municipio is not None:
        s.municipio = body.municipio or None
    if body.orgao is not None:
        s.orgao = body.orgao or None
    s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return ChatSessionOut(
        id=s.id,
        title=s.title,
        created_at=s.created_at.isoformat(),
        filters={"entity": s.entity, "estado": s.estado, "municipio": s.municipio, "orgao": s.orgao},
    )
    s = db.query(ChatSession).get(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    # delete in bulk
    count = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete(synchronize_session=False)
    s.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "cleared", "session_id": session_id, "deleted": count}


def _run_extractor_sync(entity: str, tipo: str, start: Optional[str], end: Optional[str], headless: bool):
    if entity not in datapub_cli.extractors:
        raise ValueError(f"Extractor não encontrado para entidade: {entity}")
    cls = _resolve_class(datapub_cli.extractors[entity], tipo)
    if not cls:
        raise ValueError(f"Tipo de extractor não encontrado: {tipo}")
    instance = cls()
    # Enforce headless if attribute exists
    if hasattr(instance, "headless"):
        instance.headless = headless
    instance.download(start=start, end=end)


def _run_processor_sync(entity: str, tipo: str, start: Optional[str], end: Optional[str]):
    if entity not in datapub_cli.processors:
        raise ValueError(f"Processor não encontrado para entidade: {entity}")
    cls = _resolve_class(datapub_cli.processors[entity], tipo)
    if not cls:
        raise ValueError(f"Tipo de processor não encontrado: {tipo}")
    instance = cls()
    instance.process(start=start, end=end)


@app.post("/extractor/run")
async def run_extractor(payload: TriggerExtractor, background: BackgroundTasks):
    background.add_task(
        executor.submit, _run_extractor_sync, payload.entity, payload.tipo, payload.start, payload.end, payload.headless
    )
    return {"status": "scheduled", "task": "extractor", "entity": payload.entity, "tipo": payload.tipo}


@app.post("/processor/run")
async def run_processor(payload: TriggerProcessor, background: BackgroundTasks):
    background.add_task(
        executor.submit, _run_processor_sync, payload.entity, payload.tipo, payload.start, payload.end
    )
    return {"status": "scheduled", "task": "processor", "entity": payload.entity, "tipo": payload.tipo}


@app.post("/rag/ingest")
async def rag_ingest(body: IngestBody, background: BackgroundTasks):
    entity_dir = Path("storage") / "processed" / body.entity
    if not entity_dir.exists():
        raise HTTPException(status_code=404, detail=f"Entidade sem diretório processado: {body.entity}")

    to_ingest: List[str] = []
    if body.all:
        to_ingest = [p.name for p in entity_dir.glob("*.txt")]
    elif body.file:
        p = entity_dir / body.file
        if not p.exists():
            raise HTTPException(status_code=404, detail=f"Arquivo não encontrado: {p}")
        to_ingest = [body.file]
    else:
        raise HTTPException(status_code=400, detail="Informe 'file' ou 'all=true'")

    async def _ingest_all_async():
        for f in to_ingest:
            await run_ingest(body.entity, f)

    def _runner():
        asyncio.run(_ingest_all_async())

    background.add_task(_runner)
    return {"status": "scheduled", "count": len(to_ingest)}


@app.post("/rag/prune")
async def rag_prune(background: BackgroundTasks):
    def _runner():
        asyncio.run(run_prune())

    background.add_task(_runner)
    return {"status": "scheduled", "task": "prune"}
# --------- API Key Auth (optional) ---------
EXEMPT_PATHS = {"/", "/health", "/metrics", "/docs", "/openapi.json", "/favicon.ico"}


def _get_configured_api_keys() -> set[str]:
    # Comma-separated API keys in env: API_KEYS or single API_KEY
    keys = os.getenv("API_KEYS") or os.getenv("API_KEY") or ""
    parsed = {k.strip() for k in keys.split(",") if k.strip()}
    return parsed


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    # Enforce only if keys are configured
    allowed = _get_configured_api_keys()
    # Always allow preflight requests to flow for CORS
    if request.method == "OPTIONS":
        return await call_next(request)
    if not allowed or request.url.path in EXEMPT_PATHS:
        return await call_next(request)

    hdr = request.headers.get("X-API-Key")
    if not hdr:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            hdr = auth[7:].strip()

    if not hdr or hdr not in allowed:
        return Response(status_code=401)

    return await call_next(request)
class StateOut(BaseModel):
    id: int
    nome: str
    uf: str
    ibge_id: Optional[int]
    regiao_nome: Optional[str]
    regiao_sigla: Optional[str]


class MunicipalityOut(BaseModel):
    id: int
    nome: str
    uf: str
    estado_nome: str
    ibge_id: Optional[int]

@app.get("/estados", response_model=List[StateOut])
async def list_states(
    order: Optional[str] = "nome",
    order_dir: Optional[str] = "asc",
    regiao_sigla: Optional[str] = None,
    regiao_nome: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db=Depends(get_db), request: Request = None, response: Response = None,
):
    # Choose base column
    if order == "ibge_id":
        col = State.ibge_id
    elif order == "uf":
        col = State.uf
    else:
        col = State.name
    # Direction
    if (order_dir or "asc").lower() == "desc":
        ob = col.desc()
    else:
        ob = col.asc()
    q = db.query(State)
    if regiao_sigla:
        q = q.filter(State.region_code == regiao_sigla.upper())
    if regiao_nome:
        q = q.filter(State.region_name.ilike(f"%{regiao_nome}%"))
    total = q.count()
    rows = q.order_by(ob, State.id.asc()).limit(limit).offset(offset).all()
    out = [
        StateOut(id=r.id, nome=r.name, uf=r.uf, ibge_id=r.ibge_id, regiao_nome=r.region_name, regiao_sigla=r.region_code)
        for r in rows
    ]
    if request is not None and response is not None:
        set_pagination_headers(request, response, limit, offset, total)
    return out


@app.get("/municipios", response_model=List[MunicipalityOut])
async def list_municipios(
    uf: Optional[str] = None,
    q: Optional[str] = None,
    order: Optional[str] = "nome",
    order_dir: Optional[str] = "asc",
    limit: int = 100,
    offset: int = 0,
    db=Depends(get_db), request: Request = None, response: Response = None,
):
    query = db.query(Municipality, State).join(State, Municipality.state_id == State.id)
    if uf:
        query = query.filter(State.uf == uf.upper())
    if q:
        query = query.filter(Municipality.name.ilike(f"%{q}%"))
    if order == "ibge_id":
        col = Municipality.ibge_id
    else:
        col = Municipality.name
    if (order_dir or "asc").lower() == "desc":
        ob = col.desc()
    else:
        ob = col.asc()
    total = query.count()
    rows = query.order_by(ob, Municipality.id.asc()).limit(limit).offset(offset).all()
    out = [
        MunicipalityOut(
            id=m.id,
            nome=m.name,
            uf=s.uf,
            estado_nome=s.name,
            ibge_id=m.ibge_id,
        )
        for m, s in rows
    ]
    if request is not None and response is not None:
        set_pagination_headers(request, response, limit, offset, total)
    return out


# --------- Orgaos Listing ---------
class OrgaoOut(BaseModel):
    id: int
    nome: str
    tipo: str
    uf: Optional[str]
    estado_nome: Optional[str]
    municipio_nome: Optional[str]


@app.get("/orgaos", response_model=List[OrgaoOut])
async def list_orgaos(
    uf: Optional[str] = None,
    municipio: Optional[str] = None,
    tipo: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db=Depends(get_db), request: Request = None, response: Response = None,
):
    query = db.query(Orgao, State, Municipality).\
        outerjoin(State, Orgao.state_id == State.id).\
        outerjoin(Municipality, Orgao.municipality_id == Municipality.id)

    if uf:
        query = query.filter(State.uf == uf.upper())
    if municipio:
        query = query.filter(Municipality.name.ilike(f"%{municipio}%"))
    if tipo:
        query = query.filter(Orgao.tipo.ilike(f"%{tipo}%"))
    if q:
        query = query.filter(Orgao.name.ilike(f"%{q}%"))

    total = query.count()
    rows = query.order_by(Orgao.name.asc()).limit(limit).offset(offset).all()
    out = [
        OrgaoOut(
            id=o.id,
            nome=o.name,
            tipo=o.tipo,
            uf=s.uf if s else None,
            estado_nome=s.name if s else None,
            municipio_nome=m.name if m else None,
        )
        for o, s, m in rows
    ]
    if request is not None and response is not None:
        set_pagination_headers(request, response, limit, offset, total)
    return out


# --------- Lookup by IBGE ID ---------
@app.get("/estados/{ibge_id}", response_model=StateOut)
async def get_estado_by_ibge(ibge_id: int, db=Depends(get_db)):
    r = db.query(State).filter(State.ibge_id == ibge_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Estado não encontrado")
    return StateOut(id=r.id, nome=r.name, uf=r.uf, ibge_id=r.ibge_id, regiao_nome=r.region_name, regiao_sigla=r.region_code)


@app.get("/municipios/{ibge_id}", response_model=MunicipalityOut)
async def get_municipio_by_ibge(ibge_id: int, db=Depends(get_db)):
    m = db.query(Municipality).filter(Municipality.ibge_id == ibge_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Município não encontrado")
    s = db.query(State).filter(State.id == m.state_id).first()
    return MunicipalityOut(id=m.id, nome=m.name, uf=s.uf if s else None, estado_nome=s.name if s else None, ibge_id=m.ibge_id)


# --------- Dynamic Help / Commands ---------
class HelpCommandsOut(BaseModel):
    extract_cli: List[str]
    process_cli: List[str]
    extract_api: List[Dict[str, str]]
    process_api: List[Dict[str, str]]
    ingest_cli: List[str]
    ingest_api: List[Dict[str, str]]


@app.get("/help/commands", response_model=HelpCommandsOut)
async def help_commands():
    extract_cli: List[str] = []
    process_cli: List[str] = []
    extract_api: List[Dict[str, str]] = []
    process_api: List[Dict[str, str]] = []
    ingest_cli: List[str] = []
    ingest_api: List[Dict[str, str]] = []

    # Build from CLI mappings
    for entity, types in datapub_cli.extractors.items():
        for d in types:
            for tipo in d.keys():
                extract_cli.append(
                    f"docker-compose run --rm datapub datapub {entity}_extractor {tipo} --start YYYY-MM-DD --end YYYY-MM-DD"
                )
                extract_api.append({
                    "url": "/extractor/run",
                    "body": f"{{\"entity\":\"{entity}\",\"tipo\":\"{tipo}\",\"start\":\"YYYY-MM-DD\",\"end\":\"YYYY-MM-DD\"}}",
                })
                # Suggest ingest for this entity (all)
                ingest_cli.append(
                    f"docker-compose run --rm datapub bash -lc 'for f in storage/processed/{entity}/*.txt; do ingest --entity={entity} --file=" + '"$(basename "$f")"' + "; done'"
                )
                ingest_api.append({
                    "url": "/rag/ingest",
                    "body": f"{{\"entity\":\"{entity}\",\"all\":true}}",
                })

    for entity, types in datapub_cli.processors.items():
        for d in types:
            for tipo in d.keys():
                process_cli.append(
                    f"docker-compose run --rm datapub datapub {entity}_processor {tipo} --start YYYY-MM-DD --end YYYY-MM-DD"
                )
                process_api.append({
                    "url": "/processor/run",
                    "body": f"{{\"entity\":\"{entity}\",\"tipo\":\"{tipo}\",\"start\":\"YYYY-MM-DD\",\"end\":\"YYYY-MM-DD\"}}",
                })

    return HelpCommandsOut(
        extract_cli=sorted(set(extract_cli)),
        process_cli=sorted(set(process_cli)),
        extract_api=extract_api,
        process_api=process_api,
        ingest_cli=sorted(set(ingest_cli)),
        ingest_api=ingest_api,
    )


class DefaultsOut(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None


class HelpParametersItem(BaseModel):
    entity: str
    tipo: str
    args: List[str]
    defaults: DefaultsOut


class HelpParametersOut(BaseModel):
    extractors: List[HelpParametersItem]
    processors: List[HelpParametersItem]


def _infer_defaults_from_source(cls, method_name: str) -> DefaultsOut:
    try:
        src = inspect.getsource(cls)
    except Exception:
        return DefaultsOut()
    # Pattern 1: if start is None: start = date(YYYY, M, D)
    m1 = re.search(r"if\s+start\s+is\s+None:\s*start\s*=\s*date\((\d{4}),\s*(\d{1,2}),\s*(\d{1,2})\)", src)
    if not m1:
        # Pattern 2 (processor): ... if start else date(YYYY, M, D)
        m1 = re.search(r"if\s+start\)\s*else\s*date\((\d{4}),\s*(\d{1,2}),\s*(\d{1,2})\)", src)
    start_val = None
    if m1:
        y, mo, d = m1.groups()
        start_val = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}"
    # End default: commonly today(); keep None
    return DefaultsOut(start=start_val, end=None)


def _collect_args_from_add_arguments(cls) -> List[str]:
    import argparse

    parser = argparse.ArgumentParser(add_help=False)
    try:
        cls.add_arguments(parser)  # type: ignore[attr-defined]
    except Exception:
        return []
    names: List[str] = []
    for a in parser._actions:
        for opt in a.option_strings:
            names.append(opt)
    return names


@app.get("/help/parameters", response_model=HelpParametersOut)
async def help_parameters():
    ex_items: List[HelpParametersItem] = []
    pr_items: List[HelpParametersItem] = []

    for entity, types in datapub_cli.extractors.items():
        for d in types:
            for tipo, cls in d.items():
                ex_items.append(
                    HelpParametersItem(
                        entity=entity,
                        tipo=tipo,
                        args=_collect_args_from_add_arguments(cls),
                        defaults=_infer_defaults_from_source(cls, "download"),
                    )
                )

    for entity, types in datapub_cli.processors.items():
        for d in types:
            for tipo, cls in d.items():
                pr_items.append(
                    HelpParametersItem(
                        entity=entity,
                        tipo=tipo,
                        args=_collect_args_from_add_arguments(cls),
                        defaults=_infer_defaults_from_source(cls, "process"),
                    )
                )

    return HelpParametersOut(extractors=ex_items, processors=pr_items)
# --------- Cognee helper with context ---------
async def _cognee_search(query_text: str, context: Optional[Dict] = None, metadata: Optional[Dict] = None):
    try:
        return await cognee.search(query_text=query_text, context=context, metadata=metadata)  # type: ignore[call-arg]
    except TypeError:
        # Older cognee versions may not support extra kwargs
        return await cognee.search(query_text=query_text)


def _get_int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _enforce_retention(db, session_id: int) -> None:
    max_msgs = _get_int_env("CHAT_RETENTION_MESSAGES", 0)
    if max_msgs and max_msgs > 0:
        q = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
        total = q.count()
        if total > max_msgs:
            to_delete = total - max_msgs
            ids = [
                m.id
                for m in (
                    db.query(ChatMessage)
                    .filter(ChatMessage.session_id == session_id)
                    .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
                    .limit(to_delete)
                    .all()
                )
            ]
            if ids:
                db.query(ChatMessage).filter(ChatMessage.id.in_(ids)).delete(synchronize_session=False)
                db.commit()
