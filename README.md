# 📂 DataPub – Sistema de Análise de Documentos Públicos

## 📌 Visão Geral

**DataPub** é uma plataforma para **coleta, processamento, estruturação e análise de documentos públicos brasileiros**, incluindo **Diários Oficiais, contratos, portarias, atos administrativos e demais publicações governamentais**.

Nosso objetivo é **tornar mais acessíveis e analisáveis informações que estão dispersas em portais públicos**, promovendo **transparência, accountability e inteligência institucional**.

> 🧭 **Por que isso importa?**
> Documentos públicos revelam o funcionamento real do Estado. Ao reunir e estruturar essas fontes:
>
> - Permitimos o **monitoramento da saúde política e institucional do país**
> - Fortalecemos o **controle social e o jornalismo investigativo**
> - Geramos dados úteis para **pesquisadores, ONGs, órgãos de controle e a sociedade civil organizada**

---

## Bucket Público

Os dados deste projeto estão disponíveis em um bucket da AWS com acesso público. Isso permite que qualquer pessoa acesse os arquivos diretamente, sem necessidade de autenticação.

Você pode acessar os dados por meio do seguinte endpoint (via CloudFront):

🔗 [https://d23ollh9dwoi10.cloudfront.net/](https://d23ollh9dwoi10.cloudfront.net/)

> **Nota:** Certifique-se de usar URLs completas e corretas ao referenciar arquivos específicos no bucket. Exemplo:
>
> ```
> https://d23ollh9dwoi10.cloudfront.net/pasta/arquivo.json
> ```

---

## 🗂️ Estrutura do Projeto

```

```

---

## ⚙️ Como Executar

Há duas formas de executar: via Docker (recomendado) e local.

### Via Docker (recomendado)

1) Configure variáveis de ambiente

- Copie `.env.example` para `.env` e ajuste chaves/credenciais:
  - `LLM_API_KEY`: chave da LLM suportada pelo Cognee (ex.: OpenAI)
  - Postgres/Neo4j já são criados via `docker-compose.yml` com credenciais padrão

2) Suba a stack

```
docker-compose up --build
```

Serviços expostos:
- API FastAPI: `http://localhost:8000` (docs interativas em `/docs`)
- Métricas da API: `GET /metrics` (formato Prometheus)
- Swagger UI externo: `http://localhost:8080` (consome `http://datapub:8000/openapi.json`)
  - Suporta múltiplas APIs com `URLS` (por padrão provisionado com `datapub`).
  - Também expõe um spec estático montado em `/openapi.json`. Gere-o com:

```
docker-compose run --rm datapub python scripts/export_openapi.py
```

Depois acesse o menu no Swagger UI e selecione “datapub-static”.
- Postgres: `localhost:5432`
- Neo4j: Browser em `http://localhost:7474` (login: `neo4j/pleaseletmein`)

3) Endpoints principais

- Saúde: `GET /health`
- Consulta (chat): `POST /chat/search`
  - body exemplo:
    ```json
    { "query": "licitações sobre saúde", "estado": "PA", "entity": "al_pa" }
    ```
- Disparar extractor: `POST /extractor/run`
  - body exemplo:
    ```json
    { "entity": "al_pa", "tipo": "diario", "start": "2021-01-01", "end": "2021-01-31" }
    ```
- Disparar processor: `POST /processor/run`
  - body exemplo:
    ```json
    { "entity": "al_pa", "tipo": "diario", "start": "2021-01-01", "end": "2021-01-31" }
    ```
- Ingestão RAG (Cognee): `POST /rag/ingest`
  - body exemplo (um arquivo):
    ```json
    { "entity": "al_pa", "file": "diario-al_pa-2021-01-01_2021-01-08.txt" }
    ```
  - body exemplo (todos):
    ```json
    { "entity": "al_pa", "all": true }
    ```
- Prune (limpeza): `POST /rag/prune`
- Listar documentos: `GET /documents?estado=PA&orgao=Assembleia&tipo=Diário&q=saúde&limit=20`
- Admin inicializar DB: `POST /admin/init-db`
- Rodar ETL (normalização): `POST /etl/run` body `{ "entity": "al_pa" }` (opcional)
- Geo (filtros):
  - `GET /estados`
  - `GET /estados?order=nome|ibge_id|uf&order_dir=asc|desc&regiao_sigla=N&regiao_nome=Norte`
  - `GET /municipios?uf=PA&q=Bel&order=nome|ibge_id&order_dir=asc|desc&limit=50&offset=0` (autocomplete)
  - `GET /orgaos?uf=PA&municipio=Bel%C3%A9m&tipo=municipal&q=Prefeitura&limit=50&offset=0`
  - Filtros adicionais em estados: `regiao_sigla`, `regiao_nome` (ex.: `GET /estados?regiao_sigla=N`)
  - Lookups por IBGE: `GET /estados/{ibge_id}`, `GET /municipios/{ibge_id}`

- Paginação
  - Endpoints de listagem retornam cabeçalhos:
    - `X-Total-Count`: total de registros no filtro
    - `Link`: links de paginação (`first`, `last`, `next`, `prev`)

10) Autenticação (API Key)

- Por padrão (dev), a API fica aberta localmente. Para proteger os endpoints, defina `API_KEYS` no `.env` com uma lista de chaves separadas por vírgula.
- Envio da chave:
  - Header `X-API-Key: <sua-chave>` ou `Authorization: Bearer <sua-chave>`
- Geração de chave (exemplos):
  - `python -c "import secrets; print(secrets.token_urlsafe(32))"`
  - `openssl rand -hex 32`
- Rotação: basta alterar `API_KEYS` e reiniciar o serviço da API; é possível manter múltiplas chaves ao mesmo tempo.
- Endpoints públicos (não exigem chave): `/health`, `/metrics`, `/docs`, `/openapi.json`.

8) Banco de Dados (relacional)

- Inicializar o schema:

```
docker-compose run --rm datapub bash -lc ./scripts/init_app_db.sh
```

Ou usando o serviço one‑shot dedicado:

```
docker-compose run --rm app-db-init
```

- Popular com metadados (ETL simplificado a partir de `storage/raw/*/metadata/*.json`):

```
docker-compose run --rm datapub etl
```

- Sincronizar estados e municípios (IBGE):

```
docker-compose run --rm datapub etl-ibge
# ou via API: POST /admin/sync-ibge
# ou serviço one-shot dedicado
docker-compose run --rm app-db-seed-geo
```

- O ETL IBGE preenche `ibge_id` em `states` e `municipalities`, que podem ser usados em integrações futuras.
  - Estados agora possuem também `regiao_nome` e `regiao_sigla` sincronizados do IBGE.
  - Em dev, o serviço `app-db-init` já vem com `SEED_IBGE=true` para semear automaticamente após migrações.

- Buscar documentos pela API:
  - `GET /documents?estado=PA&orgao=Assembleia&tipo=Diário&q=saúde&limit=20`
  - Resposta segue estrutura normalizada (titulo, url, data_publicacao, orgao_nome/tipo/estado/cidade, tipo_documento_nome).

Notas:
- O projeto usa dois bancos Postgres distintos dentro do mesmo container `postgres`:
  - `cognee_db` (variável `DATABASE_URL`): usado internamente pelo Cognee (embeddings/estado).
  - `datapub_db` (variável `APP_DATABASE_URL`): usado pela API para os documentos normalizados e filtros.
- O compose monta `docker/postgres-init/00-create-app-db.sql` para criar `datapub_db` na primeira inicialização do Postgres.

9) URLs públicas (S3/CloudFront)

- Os arquivos são publicados em um bucket S3 acessível via CloudFront. Defina `BASE_PUBLIC_URL` (padrão: `https://d23ollh9dwoi10.cloudfront.net`).
- Padrão de paths públicos:
  - Processados (preferidos): `/storage/processed/<entity>/<arquivo>.txt`
  - Brutos (fallback): `/storage/raw/<entity>/downloads/<arquivo>.pdf`
- Exemplo:
  - `https://d23ollh9dwoi10.cloudfront.net/storage/processed/al_pa/diario-al_pa-2021-01-01_2021-01-08.txt`
- O ETL monta automaticamente a URL pública conforme a existência do arquivo processado; caso não exista, usa o caminho bruto do metadata.

10) Dicas de Teste (Checklist Rápido)

- Subir a stack completa:

```
docker-compose up --build
```

- Inicializar banco de dados (tabelas):

```
docker-compose run --rm datapub init-db
```

- Rodar ETL para popular documentos a partir de `storage/raw/*/metadata/*.json`:

```
docker-compose run --rm datapub etl
```

- Abrir a documentação interativa da API (FastAPI):

```
http://localhost:8000/docs
```

- Usar Swagger UI externo (com menu para múltiplos specs):

```
http://localhost:8080
```

- Ver métricas Prometheus:

```
# API
http://localhost:8000/metrics

# Scheduler
http://localhost:9100/metrics
```

- Prometheus e Grafana:

```
Prometheus: http://localhost:9090
Grafana:    http://localhost:3000  (login: admin / admin)
```

- Consultar documentos com filtros:

```
GET http://localhost:8000/documents?estado=PA&orgao=Assembleia&tipo=Di%C3%A1rio&q=sa%C3%BAde&limit=20
```

- (Opcional) Proteger a API com API Key: adicione `API_KEYS` ao `.env` e envie a chave em `X-API-Key` ou `Authorization: Bearer <chave>`.

11) Operações do Pipeline (Extract, Process, Ingest, Prune)

- Listar entidades e tipos suportados (API):

```
curl http://localhost:8000/entities
```

- Extract (coleta de arquivos brutos)
  - Via CLI (Docker Compose):

```
docker-compose run --rm datapub datapub al_pa_extractor diario --start 2021-01-01 --end 2021-01-08
docker-compose run --rm datapub datapub al_go_extractor diario --start 2007-08-01 --end 2007-08-31
```

  - Via API:

```
curl -X POST http://localhost:8000/extractor/run \
  -H 'Content-Type: application/json' \
  -d '{
        "entity": "al_pa",
        "tipo": "diario",
        "start": "2021-01-01",
        "end": "2021-01-08",
        "headless": true
      }'
```

- Process (extração de texto / OCR)
  - Via CLI:

```
docker-compose run --rm datapub datapub al_pa_processor diario --start 2021-01-01 --end 2021-01-08
```

  - Via API:

```
curl -X POST http://localhost:8000/processor/run \
  -H 'Content-Type: application/json' \
  -d '{
        "entity": "al_pa",
        "tipo": "diario",
        "start": "2021-01-01",
        "end": "2021-01-08"
      }'
```

- Ingest (RAG/Cognee)
  - Um arquivo específico (CLI):

```
docker-compose run --rm datapub ingest --entity=al_pa --file=diario-al_pa-2021-01-01_2021-01-08.txt
```

  - Todos os arquivos processados de uma entidade (API):

```
curl -X POST http://localhost:8000/rag/ingest \
  -H 'Content-Type: application/json' \
  -d '{"entity":"al_pa","all":true}'
```

  - Loop (CLI) para ingerir todos (opcional):

```
docker-compose run --rm datapub bash -lc 'for f in storage/processed/al_pa/*.txt; do ingest --entity=al_pa --file="$(basename "$f")"; done'
```

- Prune (limpeza do Cognee)
  - CLI:

```
docker-compose run --rm datapub prune
```

  - API:

```
curl -X POST http://localhost:8000/rag/prune
```

- Busca (Cognee)
  - CLI:

```
docker-compose run --rm datapub query --query 'nomeações em 2021'
```

  - API (Chat Search):

```
curl -X POST http://localhost:8000/chat/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"licitações saúde","entity":"al_pa","estado":"PA"}'
```

- Chat com histórico e streaming
  - Criar sessão com filtros padrões (persistidos):

```
curl -X POST http://localhost:8000/chat/sessions \
  -H 'Content-Type: application/json' \
  -d '{"title":"meu chat","entity":"al_pa","estado":"PA","municipio":"Belém","orgao":"ALEPA"}'
```

  - Perguntar (síncrono, usa histórico recente):

```
curl -X POST http://localhost:8000/chat/sessions/<ID>/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"licitações saúde","history_limit":10}'
```

  - Perguntar (stream SSE):

```
curl -N -X POST http://localhost:8000/chat/sessions/<ID>/stream \
  -H 'Accept: text/event-stream' \
  -H 'Content-Type: application/json' \
  -d '{"query":"licitações saúde","history_limit":10}'
```

  - Listar/limpar/apagar:

```
curl http://localhost:8000/chat/sessions
curl http://localhost:8000/chat/sessions/<ID>/messages
curl -X DELETE http://localhost:8000/chat/sessions/<ID>/messages
curl -X DELETE http://localhost:8000/chat/sessions/<ID>
```

Integração com Cognee (contexto)
- A API envia ao Cognee, quando suportado, um `context` estruturado com:
  - `session_id`: ID da sessão de chat
  - `filters`: lista de filtros ativos (`entity`, `estado`, `municipio`, `orgao`)
  - `history`: últimas mensagens com `{role, content, created_at}`
- Também envia `metadata` com os filtros para enriquecer a busca.
- Para versões do Cognee sem suporte a `context`/`metadata`, a API concatena os filtros e trechos do histórico ao `query_text` como fallback.

Configuração
- `CHAT_HISTORY_LIMIT` (opcional): padrão de quantas mensagens recentes incluir no contexto (default: 10).

- Reset do banco do Cognee (caso haja erro de schema após atualizar versão)

```
# Apaga e recria o banco cognee_db, e garante a extensão pgvector
docker-compose run --rm datapub bash -lc ./scripts/reset_cognee_db.sh

# Em seguida, rode novamente a ingestão / prune conforme necessário
```

- Dicas dinâmicas (geradas pela própria API):

```
curl http://localhost:8000/help/commands | jq
# Retorna exemplos dinâmicos (CLI/API) de extract/process/ingest baseados nas entidades/tipos registrados no datapub.cli
```

- Parâmetros e defaults inferidos (por entidade/tipo):

```
curl http://localhost:8000/help/parameters | jq
# Mostra os args aceitos (ex.: --start, --end) e, quando possível, a data inicial padrão inferida do código
```

4) Cronjobs (scheduler)

- Um único job agenda a pipeline completa (todas as entidades selecionadas) diariamente às 03:00 UTC.
- Variáveis úteis (serviço `scheduler`):
  - `CRON_PIPELINE` (padrão: `0 3 * * *`)
  - `ENTITIES` (ex.: `al_pa,al_go` — se omitido, roda para todas com extractor)
  - `START` e `END` como padrão global
  - `<ENTITY>_START` e `<ENTITY>_END` para sobrescrever por entidade

5) Métricas e Logs

- Scheduler expõe métricas Prometheus em `:9100/metrics` (mapeado para `localhost:9100`). Principais métricas:
  - `datapub_pipeline_runs_total`
  - `datapub_entity_extract_seconds{entity=...}` e `datapub_entity_process_seconds{entity=...}`
  - `datapub_entity_extract_errors_total{entity=...}` e `datapub_entity_process_errors_total{entity=...}`
  - `datapub_pipeline_last_run_timestamp`, `datapub_last_extract_success_timestamp{entity=...}` e `datapub_last_process_success_timestamp{entity=...}`
- Logs estruturados (JSON) no scheduler:
  - Eventos: `scheduler_start`, `metrics_server_listen`, `pipeline_start/pipeline_end`, `extract_*`, `process_*`
  - Ajuste o nível com `LOG_LEVEL` (ex.: `DEBUG`, `INFO`)

6) Observabilidade (Prometheus/Grafana)

- Config de exemplo do Prometheus em `monitoring/prometheus.yml` (scrape de API e scheduler quando em rede do compose):

```
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: "datapub_api"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["datapub:8000"]

  - job_name: "datapub_scheduler"
    metrics_path: "/metrics"
    static_configs:
      - targets: ["datapub-scheduler:9100"]
```

- Rodar Prometheus standalone (fora do compose):

```
docker run -d --name prometheus \
  -p 9090:9090 \
  -v $(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml \
  --network container:datapub \
  prom/prometheus
```

Alternativas:
- Em rede do compose, usar `--network datapub_default` (ou o nome da rede gerada). Ou adicionar um serviço `prometheus` ao `docker-compose.yml` apontando para esse arquivo.
- Para Grafana: `docker run -d -p 3000:3000 grafana/grafana` e configurar a fonte de dados Prometheus (URL do Prometheus).

7) API Specs (OpenAPI/Swagger)

- A API expõe o spec dinâmico em `GET /openapi.json` e UI em `/docs`.
- Serviço Swagger UI externo incluso no `docker-compose.yml` em `http://localhost:8080` apontando para `datapub:8000/openapi.json`.
- Para exportar uma cópia estática local do spec:

```
docker-compose run --rm datapub python scripts/export_openapi.py
# Resultado em ./openapi/openapi.json
```

### Execução local (desenvolvimento)

1) Ambiente Python

```
python -m venv .venv
source .venv/bin/activate
pip install -e '.[sqlalchemy,testing]'
```

2) Iniciar API

```
uvicorn datapub.api.main:app --host 0.0.0.0 --port 8000
```

3) CLI utilitários (PyScaffold entry points)

- Extract/Process via CLI:
  - `datapub al_pa_extractor diario --start 2021-01-01 --end 2021-01-08`
  - `datapub al_pa_processor diario --start 2021-01-01 --end 2021-01-08`

4) RAG (Cognee)

- Ingestão: `ingest --entity=al_pa --file=diario-al_pa-2021-01-01_2021-01-08.txt`
- Busca: `query --query="nomeações em 2021"`
- Prune: `prune`

---

## 🔍 Casos de Uso

- Monitoramento de nomeações, exonerações e licitações
- Extração de padrões temáticos de portarias e contratos
- Análise de linguagem em atos administrativos
- Detecção de eventos políticos importantes em diferentes esferas (municipal, estadual, federal)

---

## 🏗️ Arquitetura Implementada

- Coleta (Extractors):
  - Classes por entidade em `src/datapub/entities/.../extractors`, com base comum em `ExtractorBase`.
  - Metadados e arquivos brutos em `storage/raw/<entity>`.
- Processamento (Processors):
  - OCR e extração de texto em `src/datapub/entities/.../processors`, base `ProcessorBase`.
  - Saída em `storage/processed/<entity>`.
- RAG (Cognee):
  - Ingestão de texto e visualização (`src/datapub/rag/ingest.py`).
  - Busca semântica (`src/datapub/rag/query.py`).
  - Limpeza de dados/estado (`src/datapub/rag/prune.py`).
- API (FastAPI):
  - `src/datapub/api/main.py` com endpoints de chat (Cognee) e triggers de extração/processamento.
- Agendador (APScheduler):
  - `src/datapub/scheduler.py` agenda rotinas diárias no contêiner `scheduler`.

Observação: Alguns extractors usam Selenium/Chromium (headless) e Tesseract (OCR). A imagem Docker foi atualizada para suportar esses requisitos.


## 🤝 Contribuições

Contribuições são muito bem-vindas!
Abra uma **issue**, envie um **pull request** ou compartilhe fontes/documentos de interesse público que deseja ver monitorados aqui.

---

## 📄 Licença

Este projeto é de código aberto sob a [MIT License](LICENSE).

---
