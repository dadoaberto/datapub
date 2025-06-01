# 📂 **DataPub – Sistema de Análise de Documentos Públicos**

🚀 Vamos juntos fazer esse projeto acontecer! 💡

Para que possamos avançar de verdade, precisamos de uma grande força-tarefa — e isso só será possível com a ajuda de vocês! 💪💙

Ainda temos muita coisa para desenvolver até que esse sonho se torne 100% realidade. Por isso, definimos uma meta inicial de R$600 em doações mensais 🙏. Com esse apoio, poderemos investir mais tempo, dedicação e mão de obra para tirar tudo do papel! 🛠️✨

Se você acredita na ideia e quer fazer parte disso, considere nos apoiar:

[![Apoie no GitHub Sponsors](https://img.shields.io/badge/Apoiar_no_GitHub_Sponsors-💖-ff69b4?style=for-the-badge)](https://github.com/sponsors/a21ns1g4ts)

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

## 🗺️ Roadmap

### **Fase 1: Coleta Automatizada (Em Andamento)**
- [x] Criar scrapers (AL-GO, AL-MS, AL-PE implementados)
- [ ] Implementar downloaders automatizados com agendamento (schedule)
- [ ] Adicionar tratamento de erros e redundância de fontes

### **Fase 2: Processamento de Arquivos**
- [ ] Extração de texto de PDFs/HTMLs (OCR quando necessário)
- [ ] Limpeza de dados (remoção de lixo digital, normalização)

### **Fase 3: Estruturação de Dados**
- [ ] Classificação por tipo de documento (contratos, portarias, licitações)
- [ ] Metadados padronizados (órgão, data, assunto, entidades mencionadas)

### **Fase 4: Análise Inteligente**
- [ ] Modelos de NLP para detecção de padrões suspeitos
- [ ] Chatbot de consulta (ex: "Quais contratos com valor acima de R$1M em 2023?")

### **Fase 5: Disponibilização Pública**
- [ ] API aberta para desenvolvedores
- [ ] Interface web acessível a não técnicos

## 📌 Fontes Implementadas

| Nome Normalizado | Nome | URL | Status |
|------------------|------|-----|--------|
| assembleia_legislativa_do_estado_de_goias_al-go | Assembleia Legislativa do Estado de Goiás (AL-GO) | [Link](https://transparencia.al.go.leg.br/gestao-parlamentar/diario) | ✅ Implementado |
| assembleia_legislativa_do_estado_de_mato_grosso_do_sul_al-ms | Assembleia Legislativa do Estado de Mato Grosso do Sul (AL-MS) | [Link](https://diariooficial.al.ms.gov.br/) | ✅ Implementado |
|assembleia_legislativa_do_estado_do_para_al-pa, | Assembléia Legislativa do Estado do Pará (AL-PA) | [Link](https://www.alepa.pa.gov.br/Comunicacao/Diarios/) | ✅ Implementado |

*(Lista completa de fontes disponível no arquivo [sources.csv](data/sources.csv))*
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

