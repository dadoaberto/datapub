import time
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date
import dateparser
import argparse

from datapub.shared.utils.extractor_base import ExtractorBase


class ALACExtractor(ExtractorBase):
    def __init__(self, base_dir="storage/raw/al_ac", extractor_type="diario"):
        super().__init__(
            entity="ALAC", base_dir=base_dir, extractor_type=extractor_type
        )
        # Em transição para: https://www.al.ac.leg.br/
        self.base_url = (
            "https://aleac.tceac.tc.br/faces/paginas/publico/dec/visualizarDOE.xhtml"
        )

        self.session = requests.Session()

    def _format_date(self, date: datetime, fmt: str = "%d-%m-%Y") -> str:
        return date.strftime(fmt)

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        parser.add_argument("--start", help="Data inicial no formato YYYY-MM-DD")
        parser.add_argument("--end", help="Data final no formato YYYY-MM-DD")

    def download(self, start=None, end=None):
        if start is None:
            start = date(2011, 8, 1)
        else:
            start = dateparser.parse(start).date()

        if end is None:
            end = date.today()
        else:
            end = dateparser.parse(end).date()

        print(f"📡 Buscando edições de {start} até {end}")
            
        current_date = start

        while current_date <= end:
            try:
                self._download_single(current_date)
            except Exception as e:
                print(f"❌ Erro em {current_date}: {e}")
            current_date += timedelta(days=1)

    def _download_single(self, target_date: date):
        filename = f"diario-al_ac-{target_date.strftime('%Y-%m-%d')}.pdf"
        filepath = self.downloads_dir / filename

        date_str = target_date.strftime("%Y-%m-%d")

        if filepath.exists():
            print(f"⏭️ [{date_str}] Já existe, pulando.")
            return True

        time.sleep(2)

        print(f"📡 Consultando ALAC para {target_date}")

        params = {
            "faces-redirect": "true",
            "includeViewParams": "true",
            "dataDEC": self._format_date(target_date),
        }

        response = self.session.get(self.base_url, params=params)
        if response.status_code != 200:
            print(
                "❌ Não foi possível carregar a página inicial:", response.status_code
            )
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
        download_response = self.session.post(
            self.base_url, data=post_data, headers=headers
        )

        content_type = download_response.headers.get("Content-Type", "")
        if "application/pdf" not in content_type:
            print("⚠️ Nenhum PDF disponível em", target_date.strftime("%Y-%m-%d"))
            return

        filename = f"diario-al_ac-{target_date.strftime('%Y-%m-%d')}.pdf"
        local_path = self.downloads_dir / filename

        with open(local_path, "wb") as f:
            f.write(download_response.content)

        file_hash = hashlib.md5(download_response.content).hexdigest()
        self._save_metadata(filename, self.base_url, local_path, "pdf", file_hash)
        print(f"✅ PDF salvo: {date_str} | Hash: {file_hash[:8]}")


if __name__ == "__main__":
    extractor = ALACExtractor()

    start_date = datetime.date(2011, 8, 1)
    end_date = datetime.now().date()

    print(
        f"🚀 Iniciando download de diários oficiais da AL-AC de {start_date} a {end_date}"
    )

    extractor.download(start_date, end_date)

    extractor.close()
