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

    def _download_single(self, day: datetime):
        day_str = day.isoformat() 

        for f in self.downloads_dir.iterdir():
            name = f.name

            if name == f"diario-al_pa-{day_str}.pdf":
                print(f"⏭️ Já existe (exato): {name}")
                return

            match = re.match(r"diario-al_pa-(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})\.pdf", name)
            if match:
                start_str, end_str = match.groups()
                try:
                    start_date = datetime.fromisoformat(start_str).date()
                    end_date = datetime.fromisoformat(end_str).date()
                    if start_date <= day <= end_date:
                        print(f"⏭️ Já existe (intervalo): {name}")
                        return
                except ValueError                   :
                    continue 

        print(f"📅 Buscando: {day.strftime('%d/%m/%Y')}")
        self.driver.get(self.base_url)

        sleep_time = random.uniform(0.1, 0.3)
        time.sleep(sleep_time)

        try:
            date_str = day.strftime("%d/%m/%Y")

            input_field = self.wait.until(EC.presence_of_element_located((By.ID, "dateEdit_I")))
            input_field.clear()

            calendar_button = self.driver.find_element(By.ID, "dateEdit_B-1")
            calendar_button.click()

            time.sleep(random.uniform(0.1, 0.3))

            input_field.send_keys(date_str)

            ActionChains(self.driver).send_keys(Keys.TAB).perform()

            time.sleep(random.uniform(0.1, 0.3))

            button = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Visualizar o arquivo')]")
            if not button:
                print(f"⚠️ Nenhum diário para {day.strftime('%d/%m/%Y')}")
                return

            button[0].click()
            time.sleep(4)

            if len(self.driver.window_handles) < 2:
                print(f"❌ PDF não abriu em nova aba para {day.strftime('%d/%m/%Y')}")
                return

            self.driver.switch_to.window(self.driver.window_handles[-1])
            pdf_url = self.driver.current_url
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

            self._download_pdf(pdf_url, day)

        except Exception as e:
            print(f"❌ Erro em {day.strftime('%d/%m/%Y')}: {e}")

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
