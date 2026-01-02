DataPub – ETL e RAG de ponta a ponta

Este documento explica, de forma prática e detalhada, como funciona o fluxo completo do DataPub: desde a coleta dos documentos (Extract/Process), passando pela normalização para banco relacional (ETL), ingestão no RAG com Cognee e, por fim, a consulta via API/Chat. Também descreve a persistência dos dados e como cada camada se relaciona.

Visão Geral do Fluxo

- Coleta (Extractors)
  - Busca arquivos brutos (PDFs) nos portais públicos e salva em `storage/raw/<entity>/downloads`.
  - Salva metadados por arquivo em `storage/raw/<entity>/metadata/metadata_<arquivo>.json`.
- Processamento (Processors)
  - Extrai texto (OCR quando necessário) e grava `.txt` em `storage/processed/<entity>/`.
- ETL (Normalização)
  - Lê os metadados da coleta e cria registros normalizados no Postgres (estados, municípios, órgãos, tipos de documento e documentos), com URLs públicas prontas (CloudFront/S3).
- RAG (Cognee)
  - Ingesta os textos processados no Cognee, gera embeddings (em Postgres/pgvector) e conhecimento estruturado (grafo em Neo4j) e disponibiliza busca semântica.
- API/Chat
  - Endpoints para disparar Extract/Process/RAG, listar documentos (com filtros) e consultar o grafo/semântica via `cognee.search`.

Persistência de Dados

- Arquivos em disco (montados em Docker via volume):
  - `storage/raw/<entity>/downloads`: PDFs originais.
  - `storage/raw/<entity>/metadata`: metadados da coleta.
  - `storage/processed/<entity>`: texto extraído (.txt) e metadados de processamento.
  - `storage/structured/<entity>`: artefatos derivados (por ex. HTML de visualização do grafo).
  - `storage/search_results`: resultados de buscas salvos pelo utilitário `query` (opcional).
- Banco relacional (Postgres):
  - Tabelas: `states`, `municipalities`, `orgaos`, `document_types`, `documents`.
  - Operações via SQLAlchemy (ORM) e migrações Alembic.
- Vetores/Embeddings (Postgres + pgvector):
  - O Cognee armazena embeddings de textos em Postgres usando a extensão pgvector.
- Grafo do Conhecimento (Neo4j):
  - Cognee estrutura relações e conceitos; endpoints de visualização podem gerar HTML salvo em `storage/structured/<entity>`.

Coleta (Extractors)

- Localização: `src/datapub/entities/*/extractors/`
- Base: `ExtractorBase`
  - Gerencia diretórios de `downloads` e `metadata`.
  - Implementa `_save_metadata` com dados do arquivo (hash, tamanho, URL origem, caminho local, etc.).
- Exemplo de metadado salvo (`storage/raw/al_pa/metadata/metadata_<arquivo>.json`):
  - `entity`, `type`, `filename`, `url` (origem), `source`, `path`, `file_type`, `file_size`, `hash_md5`, `status`, `download_at`.

Processamento (Processors)

- Localização: `src/datapub/entities/*/processors/`
- Base: `ProcessorBase`
  - Implementa `extract_text` (OCR com Tesseract quando necessário) e salva `.txt` em `storage/processed/<entity>`.
- Exemplo atual: `ALPAProcessor` (OCR por página via pdfplumber + Tesseract).

ETL (Normalização para Postgres)

- Script: `src/datapub/etl/normalize.py`
- Objetivos:
  - Ler metadados em `storage/raw/<entity>/metadata` e criar entradas normalizadas em Postgres.
  - Mapear entidade → órgão/UF/tipo (a partir de `sources.json` e heurísticas); criar/atualizar `State`, `Orgao`, `DocumentType`, `Document`.
  - Inferir `publication_date` a partir do nome do arquivo (primeira data AAAA-MM-DD detectada).
  - Gerar URL pública do documento seguindo o padrão do CloudFront S3.
- Geração de URL pública:
  - Variável `BASE_PUBLIC_URL` (padrão: `https://d23ollh9dwoi10.cloudfront.net`).
  - Preferência por texto processado (`/storage/processed/<entity>/<stem>.txt`).
  - Fallback para caminho bruto do metadata (`/storage/raw/<entity>/downloads/<arquivo>.pdf`).
- Como rodar:
  - Criar tabelas: `docker-compose run --rm datapub init-db` (ou `alembic upgrade head`).
  - Popular documentos: `docker-compose run --rm datapub etl`.

RAG com Cognee

- Ingestão (`src/datapub/rag/ingest.py`):
  - Lê arquivo `.txt` de `storage/processed/<entity>`, faz `await cognee.add(content)` e `await cognee.cognify()`.
  - Gera visualização (`visualize_graph`) opcional, salvando `.html` em `storage/structured/<entity>`.
- Busca (`src/datapub/rag/query.py`):
  - `await cognee.search(query_text=...)` retorna resultados semânticos.
  - Salva JSON em `storage/search_results` (opcional).
- Prune (`src/datapub/rag/prune.py`):
  - `await cognee.prune.prune_data()` e `await cognee.prune.prune_system(metadata=True)` para limpeza.
- Persistência (infra Cognee):
  - Postgres: índices/embeddings via `pgvector`.
  - Neo4j: grafo de conhecimento. Variáveis em `.env` já configuram `NEO4J_*` e `DATABASE_URL`.

API e Triggers

- API FastAPI: `src/datapub/api/main.py`
  - `POST /extractor/run` → agenda execução de extractor.
  - `POST /processor/run` → agenda processamento de texto.
  - `POST /rag/ingest` → agenda ingestão Cognee para um arquivo ou todos.
  - `POST /rag/prune` → agenda prune do Cognee.
  - `GET /documents` → lista documentos do Postgres com filtros `estado`, `municipio`, `orgao`, `tipo`, `q`, `limit`, `offset`.
  - `POST /admin/init-db` → cria schema no banco relacional.
  - `POST /etl/run` → agenda ETL para uma `entity` (opcional) em background.
  - Chat semântico: `POST /chat/search` (monta query com filtros em contexto e chama `cognee.search`).
- Autenticação por API Key (opcional):
  - Defina `API_KEYS` no `.env`. Envie `X-API-Key` ou `Authorization: Bearer <chave>`.
  - Endpoints públicos: `/health`, `/metrics`, `/docs`, `/openapi.json`.

Agendamento (Cron Único)

- `src/datapub/scheduler.py` (APScheduler):
  - Um único job `pipeline` roda Extract→Process para todas as entidades (ou subconjunto definido em `ENTITIES`).
  - CRON via `CRON_PIPELINE` (padrão `0 3 * * *`).
  - Datas globais por `START/END` e, por entidade, `<ENTITY>_START/END`.
  - Logs (JSON) e métricas (Prometheus) expostas em `9100/metrics`.

Passo a Passo – do zero ao chat

1) Subir a stack:
   - `docker-compose up --build`
2) (Opcional) Proteger API com chave:
   - Edite `.env`: `API_KEYS=minhaChaveSuperSecreta`
   - Recrie o serviço `datapub` (API).
3) Criar schema do banco:
   - `docker-compose run --rm datapub init-db`
   - Ou: `docker-compose run --rm datapub bash -lc "alembic upgrade head"`
4) Disparar coleta (Extract):
   - API: `POST /extractor/run` com body `{ "entity": "al_pa", "tipo": "diario", "start": "2021-01-01", "end": "2021-01-08" }`
   - CLI (direto): `datapub al_pa_extractor diario --start 2021-01-01 --end 2021-01-08`
5) Processar texto (Process):
   - API: `POST /processor/run` com body `{ "entity": "al_pa", "tipo": "diario" }`
   - CLI (exemplo AL-PA): `datapub al_pa_processor diario --start ... --end ...`
6) Normalizar para Postgres (ETL):
   - CLI: `docker-compose run --rm datapub etl`
   - API: `POST /etl/run` com body `{ "entity": "al_pa" }` (opcional)
7) Ingestão para RAG (Cognee):
   - API: `POST /rag/ingest` com body `{ "entity": "al_pa", "file": "<arquivo>.txt" }` ou `{ "entity": "al_pa", "all": true }`
   - CLI: `ingest --entity=al_pa --file=<arquivo>.txt`
8) Consulta/Chat:
   - API: `POST /chat/search` com body `{"query":"...", "estado":"PA", "entity":"al_pa"}`
   - A API adiciona os filtros ao contexto da query e chama `cognee.search`.
9) (Opcional) Visualização/Observabilidade:
   - Swagger UI: `http://localhost:8080` (menu com spec dinâmico e estático)
   - Prometheus: `http://localhost:9090`
   - Grafana: `http://localhost:3000` (dashboard “DataPub Overview”)

Boas Práticas e Extensões

- Enriquecimento de ETL
  - Expandir `sources.json` para cobrir mais entidades.
  - Ampliar heurísticas para identificar município/cidade e associar `Municipality`.
  - Extrair `description` (quando possível) dos metadados/processor.
- Filtros no Chat (RAG)
  - Hoje a API compõe o contexto com filtros; para filtros “hard” no RAG, persistir metadados adicionais no Cognee e aplicar filtro pré/pós-query.
- Segurança
  - Em produção, ative `API_KEYS` e limite endpoints públicos.
  - Considere OAuth2/JWT para controle granular por usuário.
- Migrações Alembic
  - Use `alembic revision --autogenerate -m "mensagem"` e `alembic upgrade head` para evoluir o schema.

Para dúvidas ou ajustes no pipeline (novas fontes, novos tipos de documento, mapeamentos de órgãos, etc.), abra uma issue ou solicite uma extensão no ETL/Extractors/Processors.

