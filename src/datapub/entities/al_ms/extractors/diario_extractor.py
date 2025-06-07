from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta, date
import dateparser
import time
import hashlib
from pathlib import Path
import argparse
import requests

from datapub.shared.utils.extractor_base import ExtractorBase


class ALMSExtractor(ExtractorBase):
    def __init__(self, base_dir="storage/raw/al_ms", extractor_type="diario"):
        super().__init__(
            entity="ALMS", base_dir=base_dir, extractor_type=extractor_type
        )
        self.base_url = "https://diariooficial.al.ms.gov.br/"
        self.max_attempts = 2

        self.downloads_dir.mkdir(parents=True, exist_ok=True)

        chrome_options = Options()
        chrome_options.add_experimental_option(
            "prefs",
            {
                "download.default_directory": str(self.downloads_dir.resolve()),
                "download.prompt_for_download": False,
                "plugins.always_open_pdf_externally": True,
                "download.directory_upgrade": True,
            },
        )

        if self.headless:
            print("🚀 Headless mode enabled")
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
        else:
            print("🚀 Headless mode disabled")

        chrome_options.add_argument("--log-level=3")

        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options,
        )
        self.wait = WebDriverWait(self.driver, 20)

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
        current_date = start

        try:
            self._prepare_browser()  # Abre apenas uma vez

            while current_date <= end:
                try:
                    self._download_single(current_date)
                    time.sleep(2)
                except Exception as e:
                    print(f"⚠️ Erro ao processar {current_date.strftime('%d/%m/%Y')}: {e}")
                current_date += timedelta(days=1)

        finally:
            self.close() 


    def _prepare_browser(self):
        self.driver.get(self.base_url)

    def _download_single(self, date_obj: date):
        date_str = date_obj.strftime("%Y-%m-%d")
        for attempt in range(1, self.max_attempts + 1):
            try:
                print(f"🔍 Tentando Diário nº {date_str} (tentativa {attempt})")

                input_field = self.wait.until(EC.presence_of_element_located((By.ID, "data")))
                input_field.clear()
                input_field.send_keys(date_obj.strftime("%d/%m/%Y"))
                time.sleep(1)

                self.driver.find_element(By.ID, "filtro").click()
                time.sleep(1)

                tabela = self.driver.find_element(By.CSS_SELECTOR, "table.table")
                linhas = tabela.find_elements(By.TAG_NAME, "tr")

                if len(linhas) <= 1:
                    print(f"🚫 Diário nº {date_str} não encontrado.")
                    return False

                initial_files = set(self.downloads_dir.glob("*.pdf"))

                for linha in linhas[1:]:
                    links = linha.find_elements(By.TAG_NAME, "a")
                    if links:
                        href = links[-1].get_attribute("href")
                        if href:
                            print(f"📥 Baixando PDF: {href}")
                            return self._download_pdf(date_str, href, initial_files)
                        else:
                            print(f"⚠️ Link vazio para {date_str}")
                return False

            except Exception as e:
                print(f"⚠️ Erro na tentativa {attempt} para {date_str}: {e}")
                time.sleep(2)

        print(f"❌ Falha após {self.max_attempts} tentativas para {date_str}")
        return False

    def _download_pdf(self, date_str, pdf_url, initial_files: set):
        print(f"📥 Baixando PDF diretamente: {pdf_url}")
        response = requests.get(pdf_url)
        if response.status_code != 200 or not response.content.startswith(b"%PDF"):
            print(f"❌ Falha ao baixar ou arquivo inválido: {date_str}")
            return False

        new_name = self.downloads_dir / f"diario-al_ms-{date_str}.pdf"
        with open(new_name, "wb") as f:
            f.write(response.content)

        if new_name.stat().st_size == 0:
            print(f"❌ Arquivo vazio: {new_name.name}")
            new_name.unlink(missing_ok=True)
            return False

        self._save_metadata(
            new_name.name, pdf_url, new_name, "pdf", self._calculate_hash(new_name)
        )
        print(f"✅ Baixado com sucesso ({new_name.stat().st_size / 1024:.2f} KB): {new_name.name}")
        return True

    def _wait_for_download(self, initial_files:set, timeout:int=60) -> Path | None:
        start = time.time()
        while time.time() - start < timeout:
            current = set(self.downloads_dir.glob("*.pdf"))
            crs = list(self.downloads_dir.glob("*.crdownload"))
            new = current - initial_files
            if new and not crs:
                return max(new, key=lambda f: f.stat().st_mtime)
            time.sleep(1)
        return None

    def _calculate_hash(self, filepath: Path) -> str:
        h = hashlib.md5()
        with filepath.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()

    def close(self):
        try:
            self.driver.quit()
        except:
            pass

if __name__ == "__main__":
    extractor = ALMSExtractor()

    start_date = datetime.date(2011, 8, 4)
    end_date = datetime.now().date()

    print(
        f"🚀 Iniciando download de diários oficiais da AL-MS de {start_date} a {end_date}"
    )

    extractor.download(start_date, end_date)

    extractor.close()
