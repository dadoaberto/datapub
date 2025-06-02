# 📂 **DataPub – Sistema de Análise de Documentos Públicos**

## 📌 Visão Geral

**DataPub** é uma plataforma para **coleta, processamento, estruturação e análise de documentos públicos brasileiros**, incluindo **Diários Oficiais, contratos, portarias, atos administrativos e demais publicações governamentais**.

Nosso objetivo é **tornar mais acessíveis e analisáveis informações que estão dispersas em portais públicos**, promovendo **transparência, accountability e inteligência institucional**.

> 🧭 **Por que isso importa?**
> Documentos públicos revelam o funcionamento real do Estado. Ao reunir e estruturar essas fontes:
>
> * Permitimos o **monitoramento da saúde política e institucional do país**
> * Fortalecemos o **controle social e o jornalismo investigativo**
> * Geramos dados úteis para **pesquisadores, ONGs, órgãos de controle e a sociedade civil organizada**

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
/datapub
│
├── /data
│   ├── /raw              # Documentos públicos originais (PDF, HTML, etc.)
│   ├── /processed        # Textos extraídos, limpos e enriquecidos
│   └── /structured       # Dados estruturados (JSON, CSV, banco de dados)
│
├── /src
│   ├── /extractors      # Robôs de coleta (scrapers, crawlers, APIs)
│       ├── al_go.py      # Assembleia Legislativa de GO
│       ├── al_ms.py      # Assembleia Legislativa de MS
│       └── ...
│   ├── /processing       # Pipelines ETL (extração, transformação, carga)
│   ├── /models           # Modelos de NLP/ML para análise de conteúdo
│   ├── /api              # Backend (FastAPI)
│   └── /frontend         # Interface interativa (Streamlit)
│
├── docker-compose.yml    # Orquestração de serviços via Docker
├── requirements.txt      # Dependências do Python
└── README.md             # Este documento
```

---

## ⚙️ Como Executar

1. **Instale as dependências**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Execute o coletor de arquivos**:

   ```bash
   python run_extractor.py al_go --start 2021-01-1 --end 2025-06-1
   ```

3. **Execute o pipeline de processamento**:

   // TODO

---

## 🔍 Casos de Uso

* Monitoramento de nomeações, exonerações e licitações
* Extração de padrões temáticos de portarias e contratos
* Análise de linguagem em atos administrativos
* Detecção de eventos políticos importantes em diferentes esferas (municipal, estadual, federal)

---

## 🤝 Contribuições

Contribuições são muito bem-vindas!
Abra uma **issue**, envie um **pull request** ou compartilhe fontes/documentos de interesse público que deseja ver monitorados aqui.

---

## 📄 Licença

Este projeto é de código aberto sob a [MIT License](LICENSE).

---

