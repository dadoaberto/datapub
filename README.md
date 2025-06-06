# 📂 **DataPub – Sistema de Análise de Documentos Públicos**

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
/datapub
│
├── /data
│   ├── /raw               # Documentos públicos originais (PDF, HTML, etc.)
│   ├── /processed         # Textos extraídos, limpos e enriquecidos
│   └── /structured        # Dados estruturados (JSON, CSV, banco de dados)
│
├── src/                   # Código fonte dentro de 'src' (modo recomendado)
│   └── databub/           # Package com seu código
│       ├── __init__.py
│       ├── extractors/    # Robôs de coleta (scrapers, crawlers, APIs)
│       │   ├── __init__.py
│       │   ├── al_pa/       
│       │   │    ├── base.py
│       │   │    ├── diario_alpa.py
│       │   │    └── relatorios_gestao_alpa.py
│       │   ├── utils/
│       │   ├── __init__.py
│       │   └── selenium_utils.py
│       ├── config.py
│       └── factory.py
│
├── tests/                 
│   ├── __init__.py
│   ├── test_diario_alpa.py
│   └── test_relatorios_gestao_alpa.py
│
├── docs/
│
├── .gitignore
├── LICENSE
├── pyproject.toml           # Configurações do projeto (PEP 518)
├── setup.cfg                # Configurações do setuptools, lint, pytest, etc
├── setup.py                 # Script de instalação
├── requirements.txt         # Dependências
└── README.rst               # Documentação

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

- Monitoramento de nomeações, exonerações e licitações
- Extração de padrões temáticos de portarias e contratos
- Análise de linguagem em atos administrativos
- Detecção de eventos políticos importantes em diferentes esferas (municipal, estadual, federal)

---

## 🤝 Contribuições

Contribuições são muito bem-vindas!
Abra uma **issue**, envie um **pull request** ou compartilhe fontes/documentos de interesse público que deseja ver monitorados aqui.

---

## 📄 Licença

Este projeto é de código aberto sob a [MIT License](LICENSE).

---
