import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional

import os
from fastapi import BackgroundTasks, FastAPI, HTTPException, Response, Request, Depends
from pydantic import BaseModel, Field
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import select

from datapub.db.base import SessionLocal
from datapub.db.models import Document, Orgao, State, Municipality, DocumentType
from datapub.db.init_db import init_db as init_db_sync
from datapub.etl.normalize import run_normalize
from datapub.etl.ibge_localidades import run_sync_ibge

# Local imports
from datapub import cli as datapub_cli
from datapub.rag.ingest import run_ingest
from datapub.rag.prune import run_prune
import cognee


app = FastAPI(title="DataPub API", version="0.1.0")


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
    query: str = Field(..., description="Texto da consulta")
    estado: Optional[str] = Field(None, description="UF do estado, ex: PA")
    municipio: Optional[str] = None
    orgao: Optional[str] = Field(None, description="Órgão público, ex: ALEPA")
    entity: Optional[str] = Field(None, description="Identificador interno, ex: al_pa")


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
    db=Depends(get_db),
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
        run_sync_ibge()

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


@app.post("/chat/search")
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

    try:
        results = await cognee.search(query_text=query_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar Cognee: {e}")

    return {
        "query": payload.query,
        "filters": filters,
        "results": results,
    }


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
EXEMPT_PATHS = {"/health", "/metrics", "/docs", "/openapi.json"}


def _get_configured_api_keys() -> set[str]:
    # Comma-separated API keys in env: API_KEYS or single API_KEY
    keys = os.getenv("API_KEYS") or os.getenv("API_KEY") or ""
    parsed = {k.strip() for k in keys.split(",") if k.strip()}
    return parsed


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    # Enforce only if keys are configured
    allowed = _get_configured_api_keys()
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


class MunicipalityOut(BaseModel):
    id: int
    nome: str
    uf: str
    estado_nome: str
    ibge_id: Optional[int]

@app.get("/estados", response_model=List[StateOut])
async def list_states(order: Optional[str] = "nome", order_dir: Optional[str] = "asc", db=Depends(get_db)):
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
    rows = db.query(State).order_by(ob, State.id.asc()).all()
    return [
        StateOut(id=r.id, nome=r.name, uf=r.uf, ibge_id=r.ibge_id) for r in rows
    ]


@app.get("/municipios", response_model=List[MunicipalityOut])
async def list_municipios(
    uf: Optional[str] = None,
    q: Optional[str] = None,
    order: Optional[str] = "nome",
    order_dir: Optional[str] = "asc",
    limit: int = 100,
    offset: int = 0,
    db=Depends(get_db),
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
    rows = query.order_by(ob, Municipality.id.asc()).limit(limit).offset(offset).all()
    return [
        MunicipalityOut(
            id=m.id,
            nome=m.name,
            uf=s.uf,
            estado_nome=s.name,
            ibge_id=m.ibge_id,
        )
        for m, s in rows
    ]
