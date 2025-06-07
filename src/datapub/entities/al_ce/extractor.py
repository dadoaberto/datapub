import os
import json
import hashlib
import requests
from pathlib import Path
from datetime import datetime, timedelta


class Extractor:
    def __init__(self, base_dir="storage/raw/alce"):
        self.base_api = "https://doalece.al.ce.gov.br/api/publico/ultimas-edicoes"
        self.base_url = "https://doalece.al.ce.gov.br"
        self.base_dir = Path(base_dir)
        self.downloads_dir = self.base_dir / "downloads"
        self.metadata_dir = self.base_dir / "metadata"

        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def _format_date(self, date: datetime):
        return date.strftime("%Y-%m-%d")

    def _build_api_url(self, start_date: datetime, end_date: datetime):
        date_range = {
            "data_de": self._format_date(start_date),
            "data_ate": self._format_date(end_date),
        }
        return f"{self.base_api}?buscarData={json.dumps(date_range)}"

    def download(self, start_date: datetime, end_date: datetime):
        print(f"📡 Buscando edições de {start_date} até {end_date}")
        api_url = self._build_api_url(start_date, end_date)
        response = requests.get(api_url)

        if response.status_code != 200:
            print("❌ Erro ao acessar a API:", response.status_code)
            return

        data = response.json()
        edicoes = data.get("dados", [])

        if not edicoes:
            print("⚠️ Nenhuma edição encontrada nesse intervalo.")
            return

        for edicao in edicoes:
            try:
                self._baixar_edicao(edicao)
            except Exception as e:
                print(f"❌ Erro ao baixar edição {edicao.get('id')}: {e}")

    def _baixar_edicao(self, edicao: dict):
        data_pub = edicao["data_publicacao"][:10]
        nome_arquivo = f"diario-alce-{data_pub}.pdf"
        caminho = edicao["caminho_documento_pdf"]
        url_pdf = self.base_url + caminho

        print(f"📄 Baixando edição de {data_pub}: {nome_arquivo}")

        response = requests.get(url_pdf, timeout=15)
        if response.status_code == 200 and b"%PDF" in response.content[:10]:
            local_path = self.downloads_dir / nome_arquivo
            with open(local_path, "wb") as f:
                f.write(response.content)

            file_hash = hashlib.md5(response.content).hexdigest()
            self._salvar_metadata(edicao, url_pdf, local_path, file_hash)
            print(f"✅ Salvo: {nome_arquivo} | Hash: {file_hash[:8]}")
        else:
            print(f"⚠️ Arquivo inválido ou não encontrado: {url_pdf}")

    def _salvar_metadata(self, edicao: dict, url_pdf: str, local_path: Path, file_hash: str):
        metadata = {
            "orgao": "ALCE",
            "data_publicacao": edicao["data_publicacao"],
            "url_origem": url_pdf,
            "caminho_local": str(local_path),
            "data_download": datetime.now().isoformat(),
            "tamanho_bytes": os.path.getsize(local_path),
            "hash_md5": file_hash,
            "status": "sucesso"
        }

        nome_metadata = f"metadata_{edicao['data_publicacao'][:10]}.json"
        with open(self.metadata_dir / nome_metadata, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    extractor = Extractor()
    try:
        inicio = datetime(2025, 5, 22)
        fim = datetime(2025, 6, 1)
        extractor.download(inicio, fim)
    except Exception as e:
        print("Erro durante execução:", e)
