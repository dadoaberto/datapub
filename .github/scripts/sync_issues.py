import json
import os
import requests
import time

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def load_json():
    with open('./sources.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def load_all_open_issue_titles():
    titles = set()
    page = 1
    while True:
        url = f"https://api.github.com/repos/{REPO}/issues?state=open&per_page=100&page={page}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"Erro ao buscar issues na página {page}: {response.text}")
            break
        issues = response.json()
        if not issues:
            break
        for issue in issues:
            titles.add(issue["title"].strip().lower())
        page += 1
    return titles

def create_issue(title, body, existing_titles):
    if title.strip().lower() in existing_titles:
        print(f"Issue already exists: {title}")
        return False

    url = f"https://api.github.com/repos/{REPO}/issues"
    data = {
        "title": title,
        "body": body
    }
    response = requests.post(url, headers=HEADERS, json=data)
    if response.status_code == 201:
        print(f"Issue created: {title}")
        # Adiciona o título criado para evitar criação duplicada na mesma execução
        existing_titles.add(title.strip().lower())
        return True
    else:
        print(f"Error creating issue {title}: {response.text}")
        return False

def main():
    data = load_json()
    existing_titles = load_all_open_issue_titles()
    created_count = 0
    max_create = 20

    for item in data:
        if created_count >= max_create:
            print(f"Limite de {max_create} issues criadas atingido nesta execução.")
            break

        title = f"Implementar pipeline para {item['nome']} ({item['sigla']})"
        body = f"""
# 🚀 Implementar pipeline para a fonte {item['nome']} ({item['sigla']})

---

## 📋 Detalhes da Fonte

- **Nome:** {item['nome']}
- **Sigla:** {item['sigla']}
- **URL:** {item['url']}

---

## 📊 Status Atual do Pipeline

- [ ] **Extracted:** {item['extracted']}  
- [ ] **Processed:** {item['processed']}  
- [ ] **Structured:** {item['structured']}  

---

## 🎯 Objetivo

Implementar a arquitetura do projeto DataPub para esta fonte, garantindo que os dados sejam extraídos, processados e estruturados corretamente para análise.

---

## 🔧 Próximas Etapas

- [ ] Validar conexão e acesso à fonte
- [ ] Implementar extração dos dados (ETL)
- [ ] Processar dados para limpeza e transformação
- [ ] Estruturar dados para consumo downstream
- [ ] Testar pipeline end-to-end

---

## 📚 Referências

Leia mais no README do projeto:  
https://github.com/{REPO}#readme

---

## 🛠️ Notas para o Bot de Automação

- Fonte: `{item['sigla']}`  
- Status Extracted: `{item['extracted']}`  
- Status Processed: `{item['processed']}`  
- Status Structured: `{item['structured']}`  
- URL Fonte: `{item['url']}`

---

_💡 Este template foi criado para facilitar a colaboração e automação no projeto DataPub._
"""
        created = create_issue(title, body, existing_titles)
        if created:
            created_count += 1
            time.sleep(1.5)  # para respeitar limite da API

if __name__ == "__main__":
    main()
