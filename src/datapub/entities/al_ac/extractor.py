import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from pathlib import Path


class Extractor:
    def __init__(self, base_dir="storage/raw/alac"):
        self.session = requests.Session()
        # Em transição para: https://www.al.ac.leg.br/
        self.base_url = "https://aleac.tceac.tc.br/faces/paginas/publico/dec/visualizarDOE.xhtml"
        self.base_dir = Path(base_dir)
        self.download_dir = self.base_dir / "downloads"
        self.metadata_dir = self.base_dir / "metadata"

        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def _format_date(self, date: datetime):
        return date.strftime("%d-%m-%Y")

    def download(self, start_date=None, end_date=None, delay=0.5):
        if end_date is None:
            end_date = datetime.date.today()
        if start_date is None:
            start_date = datetime.date(2007, 1, 1)

        current_date = start_date

        while current_date <= end_date:
            try:
                self._download_single(current_date)
            except Exception as e:
                print(f"❌ Erro em {current_date}: {e}")
            current_date += timedelta(days=1)

    def _download_single(self, target_date: datetime):
        print(f"📡 Consultando ALAC para {target_date}")

        params = {
            "faces-redirect": "true",
            "includeViewParams": "true",
            "dataDEC": self._format_date(target_date)
        }

        response = self.session.get(self.base_url, params=params)
        if response.status_code != 200:
            print("❌ Não foi possível carregar a página inicial:", response.status_code)
            return

        soup = BeautifulSoup(response.text, "html.parser")
        view_state = soup.find("input", {"name": "javax.faces.ViewState"})
        if not view_state:
            print("❌ ViewState não encontrado.")
            return

        view_state_value = view_state["value"]
        form_id = "visualizarDoe"

        post_data = {
            f"{form_id}": form_id,
            f"{form_id}:botaoDownloadLink": f"{form_id}:botaoDownloadLink",
            "javax.faces.ViewState": view_state_value,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": response.url,
        }

        print("⏬ Enviando requisição de download...")
        download_response = self.session.post(self.base_url, data=post_data, headers=headers)

        content_type = download_response.headers.get("Content-Type", "")
        if "application/pdf" not in content_type:
            print("⚠️ Nenhum PDF disponível em", target_date.strftime('%Y-%m-%d'))
            return

        nome_arquivo = f"diario-alac-{target_date.strftime('%Y-%m-%d')}.pdf"
        local_path = self.download_dir / nome_arquivo

        with open(local_path, "wb") as f:
            f.write(download_response.content)

        file_hash = hashlib.md5(download_response.content).hexdigest()
        self._salvar_metadata(target_date, local_path, file_hash)
        print(f"✅ PDF salvo: {nome_arquivo} | Hash: {file_hash[:8]}")

    def _salvar_metadata(self, target_date: datetime, local_path: Path, file_hash: str):
        metadata = {
            "orgao": "ALAC",
            "data_publicacao": target_date.strftime("%Y-%m-%d"),
            "url_origem": self.base_url,
            "caminho_local": str(local_path),
            "data_download": datetime.now().isoformat(),
            "tamanho_bytes": os.path.getsize(local_path),
            "hash_md5": file_hash,
            "status": "sucesso"
        }

        nome_metadata = f"metadata_{target_date.strftime('%Y-%m-%d')}.json"
        with open(self.metadata_dir / nome_metadata, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    extractor = Extractor()
    try:
        extractor.download(
            start_date=datetime(2015, 1, 1),
            end_date=datetime(2025, 6, 1)
        )
    except Exception as e:
        print("Erro durante execução:", e)
