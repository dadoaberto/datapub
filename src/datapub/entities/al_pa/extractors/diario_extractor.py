import time
import hashlib
import random
from datetime import datetime, timedelta, date
import re
import dateparser
import pdfplumber
import argparse

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys

from datapub.shared.utils.extractor_base import ExtractorBase

class ALPAExtractor(ExtractorBase):
    def __init__(self, base_dir="storage/raw/al_pa", extractor_type="diario"):
        super().__init__(entity="ALPA", base_dir=base_dir, extractor_type=extractor_type)

        self.base_url = "https://www.alepa.pa.gov.br/Comunicacao/Diarios"   

        chrome_options = Options()
        
        if self.headless:
            print("🚀 Headless mode enabled")
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
        else:
            print("🚀 Headless mode disabled")

        chrome_options.add_argument("--log-level=3")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        parser.add_argument("--start", help="Data inicial no formato YYYY-MM-DD")
        parser.add_argument("--end", help="Data final no formato YYYY-MM-DD")

    def download(self, start=None, end=None):
        print(f"📡 Buscando edições de {start} até {end}")
        
        if end is None:
            end = date.today()
        else:
            start = dateparser.parse(start).date()
        if start is None:
            start = date(2021, 1, 1)
        else:
            end = dateparser.parse(end).date()
            
        current_date = start
        while current_date <= end:
            try:
                self._download_single(current_date)
                time.sleep(random.uniform(0, 0.2))
            except Exception as e:
                print(f"⚠️ Erro ao processar {current_date.strftime('%d/%m/%Y')}: {e}")
            current_date += timedelta(days=1)

    def _download_pdf(self, date_str, pdf_url):
        print(f"⏳ Iniciando download do Diário {date_str}...")

        try:
            self.driver.execute_script("window.open(arguments[0], '_blank');", pdf_url)
            start_time = time.time()
            max_wait = 30
            initial_files = set(self.downloads_dir.glob("*.pdf"))

            print(f"⏳ Aguardando download do Diário {date_str}...")

            latest_file = None
            while time.time() - start_time < max_wait:
                current_files = {
                    f for f in self.downloads_dir.glob("*.pdf")
                    if not f.name.endswith(".crdownload")
                }
                new_files = current_files - initial_files
                if new_files:
                    latest_file = max(new_files, key=lambda f: f.stat().st_mtime)
                    size = latest_file.stat().st_size
                    time.sleep(2)
                    if latest_file.stat().st_size == size:
                        break
                time.sleep(1)
            else:
                print(f"❌ Timeout ao baixar Diário {date_str}")
                return False

            print(f"📄 Verificando validade do PDF para Diário {date_str}...")
            with latest_file.open("rb") as f:
                if not f.read(4).startswith(b"%PDF"):
                    print(f"❌ Arquivo inválido para Diário {date_str}")
                    latest_file.unlink(missing_ok=True)
                    return False

            new_filename = f"diario-al_ms-{date_str}.pdf"
            new_path = self.downloads_dir / new_filename

            try:
                print(f"📦 Renomeando arquivo para {new_filename}")
                latest_file.rename(new_path)
            except Exception as e:
                print(f"❌ Erro ao renomear arquivo: {str(e)}")
                self._log_error(date_str, f"Erro ao renomear: {str(e)}")
                return False

            file_size = new_path.stat().st_size
            if file_size == 0:
                print(f"❌ Arquivo vazio para Diário {date_str}")
                new_path.unlink(missing_ok=True)
                return False

            print(f"💾 Salvando metadados para Diário {date_str}")
            self._save_metadata(
                new_filename,
                pdf_url,
                new_path,
                "pdf",
                self._calculate_hash(new_path),
            )

            print(f"✅ Diário {date_str} baixado com sucesso ({file_size / 1024:.2f} KB)")
            return True

        except Exception as e:
            print(f"❌ Erro inesperado ao baixar Diário {date_str}: {str(e)}")
            self._log_error(date_str, str(e))
            return False

    def _download_pdf(self, url, day):
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200 and b"%PDF" in response.content[:10]:
                temp_filename = f"diario-al_pa-{day.isoformat()}.pdf"
                temp_path = self.downloads_dir / temp_filename

                with open(temp_path, "wb") as f:
                    f.write(response.content)

                path = temp_path 
                text = self._extract_text_from_pdf(temp_path)

                if text:
                    date_range = self._extract_date_range(text)
                    if date_range[0] and date_range[1]:
                        print(f"📋 Encontrado intervalo de datas: {date_range}")
                        final_filename = f"diario-al_pa-{date_range[0]}_{date_range[1]}.pdf"
                        final_path = self.downloads_dir / final_filename
                        temp_path.rename(final_path)
                        path = final_path  

                file_hash = hashlib.md5(response.content).hexdigest()
                self._save_metadata(temp_filename, url, path, 'pdf' ,file_hash)
                print(f"✅ Salvo: {path.name} | Hash: {file_hash[:8]}")

            else:
                print(f"⚠️ Conteúdo não é PDF válido: {url}")
        except Exception as e:
            print(f"❌ Falha ao baixar PDF: {e}")

    def _extract_text_from_pdf(self, pdf_path):
        full_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            # for page in pdf.pages:
            #     full_text += page.extract_text() + "\n"
            full_text += pdf.pages[0].extract_text()
        return full_text

    def _extract_date_range(self, text):
        patterns = [
            # 29 de Janeiro a 05 de Fevereiro de 2021
            r'(\d{1,2})\s*de\s*([a-zç]+)\s*a\s*(\d{1,2})\s*de\s*([a-zç]+)\s*de\s*(\d{4})',
            
            # 22 a 29 de Janeiro de 2021
            r'(\d{1,2})\s*a\s*(\d{1,2})\s*de\s*([a-zç]+)\s*de\s*(\d{4})',
        ]

        results = []

        for pattern in patterns:
            for match in re.finditer(pattern, text.lower()):
                groups = match.groups()

                try:
                    if len(groups) == 5:
                        # Ex: 29 de Janeiro a 05 de Fevereiro de 2021
                        start_date = dateparser.parse(f"{groups[0]} de {groups[1]} de {groups[4]}", languages=['pt'])
                        end_date = dateparser.parse(f"{groups[2]} de {groups[3]} de {groups[4]}", languages=['pt'])
                    elif len(groups) == 4:
                        # Ex: 22 a 29 de Janeiro de 2021
                        start_date = dateparser.parse(f"{groups[0]} de {groups[2]} de {groups[3]}", languages=['pt'])
                        end_date = dateparser.parse(f"{groups[1]} de {groups[2]} de {groups[3]}", languages=['pt'])
                    else:
                        continue

                    if start_date and end_date:
                        results.append((start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
                except:
                    continue

        return results[0]

    def close(self):
        self.driver.quit()

if __name__ == "__main__":
    extractor = ALPAExtractor()
    
    start_date = datetime.date(2021, 1, 1)
    end_date = datetime.now().date()

    print(f"🚀 Iniciando download de diários oficiais da AL-PA de {start_date} a {end_date}")

    extractor.download(start_date, end_date)

    extractor.close()
