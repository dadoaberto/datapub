import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import inspect
import re
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
