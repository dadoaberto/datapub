import json
import hashlib
import requests
import dateparser
import argparse

from datetime import datetime, date

from datapub.shared.utils.extractor_base import ExtractorBase


class ALCEExtractor(ExtractorBase):
    def __init__(self, base_dir="storage/raw/al_ce", extractor_type="diario"):
        super().__init__(
            entity="ALCE", base_dir=base_dir, extractor_type=extractor_type
        )

        self.base_api = "https://doalece.al.ce.gov.br/api/publico/ultimas-edicoes"
        self.base_url = "https://doalece.al.ce.gov.br"

    def _build_api_url(self, start_date: datetime, end_date: datetime):
        date_range = {
            "data_de": self._format_date(start_date),
            "data_ate": self._format_date(end_date),
        }
        return f"{self.base_api}?buscarData={json.dumps(date_range)}"

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        parser.add_argument("--start", help="Data inicial no formato YYYY-MM-DD")
        parser.add_argument("--end", help="Data final no formato YYYY-MM-DD")

    def download(self, start=None, end=None):
        if start is None:
            start = date(2011, 8, 4)
        else:
            start = dateparser.parse(start).date()

        if end is None:
            end = date.today()
        else:
            end = dateparser.parse(end).date()

        print(f"📡 Buscando edições de {start} até {end}")
        api_url = self._build_api_url(start, end)
        response = requests.get(api_url)

        if response.status_code != 200:
            print("❌ Erro ao acessar a API:", response.status_code)
            return

        data = response.json()
        edicoes = data.get("dados", [])

        if not edicoes:
            print("⚠️ Nenhuma edição encontrada nesse intervalo.")
            return

        for edition in edicoes:
            try:
                self._download_edition(edition)
            except Exception as e:
                print(f"❌ Erro ao baixar edição {edition.get('id')}: {e}")

    def _download_edition(self, edition: dict):
        data_pub = edition["data_publicacao"][:10]
        filename = f"diario-alce-{data_pub}.pdf"
        filepath = self.downloads_dir / filename

        if filepath.exists():
            print(f"⏭️ [{data_pub}] Já existe, pulando.")
            return True

        print(f"📄 Baixando edição de {data_pub}: {filename}")

        response = requests.get(filepath, timeout=15)
        if response.status_code == 200 and b"%PDF" in response.content[:10]:
            local_path = self.downloads_dir / filename
            with open(local_path, "wb") as f:
                f.write(response.content)

            file_hash = hashlib.md5(response.content).hexdigest()
            self._save_metadata(filename, filepath, local_path, "pdf", file_hash)
            print(f"✅ Salvo: {filename} | Hash: {file_hash[:8]}")
        else:
            print(f"⚠️ Arquivo inválido ou não encontrado: {filepath}")


if __name__ == "__main__":
    extractor = ALCEExtractor()

    start_date = datetime.date(2025, 5, 22)
    end_date = datetime.now().date()

    print(
        f"🚀 Iniciando download de diários oficiais da AL-CE de {start_date} a {end_date}"
    )

    extractor.download(start_date, end_date)

    extractor.close()
