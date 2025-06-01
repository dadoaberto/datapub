# 📂 **DataPub – Sistema de Análise de Documentos Públicos**

🚀 Vamos juntos fazer esse projeto acontecer! 💡

Para que possamos avançar de verdade, precisamos de uma grande força-tarefa — e isso só será possível com a ajuda de vocês! 💪💙

Ainda temos muita coisa para desenvolver até que esse sonho se torne 100% realidade. Por isso, definimos uma meta inicial de R$600 em doações mensais 🙏. Com esse apoio, poderemos investir mais tempo, dedicação e mão de obra para tirar tudo do papel! 🛠️✨

Se você acredita na ideia e quer fazer parte disso, considere nos apoiar:

<iframe src="https://github.com/sponsors/a21ns1g4ts/card" title="Sponsor a21ns1g4ts" height="225" width="600" style="border: 0;"></iframe>
❤️ Toda ajuda faz a diferença. Obrigado por caminhar com a gente! 🙌

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
│   ├── /downloaders      # Robôs de coleta (scrapers, crawlers, APIs)
│       ├── al_go.py      # Assembleia Legislativa de GO
│       ├── al_ms.py      # Assembleia Legislativa de MS
│       └── estado_sp.py  # Exemplo de órgão estadual
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

2. **Execute o coletor de um órgão**:

   ```bash
   python src/downloaders/al_go.py
   ```

3. **Execute o pipeline de processamento**:

   ```bash
   python src/processing/process_all.py
   ```

4. **Suba a API (opcional)**:

   ```bash
   uvicorn src.api.main:app --reload
   ```

5. **Inicie a interface de visualização (opcional)**:

   ```bash
   streamlit run src/frontend/main.py
   ```

---

## 🔍 Casos de Uso

* Monitoramento de nomeações, exonerações e licitações
* Extração de padrões temáticos de portarias e contratos
* Análise de linguagem em atos administrativos
* Detecção de eventos políticos importantes em diferentes esferas (municipal, estadual, federal)

---

## 🌐 Escopo Atual e Futuro

Atualmente, o DataPub contempla **Assembleias Legislativas** e **portais de transparência estaduais**, com expansão prevista para:

* Câmaras Municipais
* Tribunais de Contas
* Ministérios Federais
* Diários da Justiça
* Contratos, licitações e convênios

---

## 🤝 Contribuições

Contribuições são muito bem-vindas!
Abra uma **issue**, envie um **pull request** ou compartilhe fontes/documentos de interesse público que deseja ver monitorados aqui.

---

## 📄 Licença

Este projeto é de código aberto sob a [MIT License](LICENSE).

---

