from datetime import datetime, date
import time
import hashlib
import json
import os
from pathlib import Path
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import re
from datapub.shared.utils.extractor_base import ExtractorBase

class ALGOExtractor(ExtractorBase):
    def __init__(self):
        super().__init__(entity="ALGO", base_dir="storage/raw/al_go")
        self.base_dir = Path(base_dir)
        self.downloads_dir = self.base_dir / "downloads"
        self.metadata_dir = self.base_dir / "metadata"
        
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        self.page_url_template = "https://transparencia.al.go.leg.br/gestao-parlamentar/diario?ano={}&mes={}"

        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new") 
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
        
        self.driver = webdriver.Chrome(options=chrome_options)

    def close(self):
        self.driver.quit()

    def download(self, start_date=None, end_date=None, delay=0.5):
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = date(2007, 1, 1)

        current_date = start_date
        while current_date <= end_date:
            year = current_date.year
            month = current_date.month
            print(f"🔍 Processando {year}-{month:02d}")
            links = self._get_pdf_links_for_month(year, month)

            for date_str, url in links.items():
                self._download_single_url(date_str, url)
                time.sleep(delay)

            year = current_date.year + (current_date.month // 12)
            month = current_date.month % 12 + 1
            current_date = date(year, month, 1)

    def _get_pdf_links_for_month(self, year, month):
        url = self.page_url_template.format(year, month)
        print(f"  - Carregando página: {url}")
        self.driver.get(url)

        time.sleep(3)

        links = {}

        elements = self.driver.find_elements(By.CSS_SELECTOR, "a.fc-day-grid-event")
        for el in elements:
            href = el.get_attribute("href")
            if href and href.endswith(".pdf"):
                filename = href.split("/")[-1]
                parts = filename.split("-")
                if len(parts) >= 4:
                    date_str = parts[-1].replace(".pdf", "")
                    links[date_str] = href

        print(f"  - Encontrados {len(links)} links")
        return links

    def _download_single_url(self, date_str, url):
        match = re.search(r"diario-alego-(\d{4}-\d{2}-\d{2})\.pdf", url)
        date = match.group(1)

        filename = f"diario-alego-{date}.pdf"
        filepath = self.downloads_dir / filename

        if filepath.exists():
            print(f"⏭️ [{date_str}] Já existe, pulando.")
            return True

        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200 and b"%PDF" in response.content[:10]:
                with open(filepath, "wb") as f:
                    f.write(response.content)

                file_hash = hashlib.md5(response.content).hexdigest()
                self._save_metadata(date_str, url, filepath, file_hash)

                print(f"✅ [{date_str}] Baixado com sucesso | Hash: {file_hash[:8]}")
                return True
            else:
                print(f"⚠️ [{date_str}] Documento não encontrado ou inválido (HTTP {response.status_code})")
                return False
        except Exception as e:
            print(f"❌ [{date_str}] Erro ao baixar: {e}")
            return False

    def _save_metadata(self, date_str, url, filepath, file_hash):
        metadata = {
            "orgao": "AL-EGO",
            "data_publicacao": date_str,
            "url_origem": url,
            "caminho_local": str(filepath),
            "data_download": datetime.now().isoformat(),
            "tamanho_bytes": os.path.getsize(filepath),
            "hash_md5": file_hash,
            "status": "sucesso",
        }

        metadata_path = self.metadata_dir / f"metadata_{date_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    extractor = Extractor(headless=True)

    start_date = datetime.date(2007, 8, 1)
    end_date = datetime.date(2007, 8, 31)

    print(f"🚀 Iniciando download de diários da AL-EGO de {start_date} a {end_date}")
    extractor.download(start_date, end_date)

    extractor.close()
