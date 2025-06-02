import time
import os
import json
import hashlib
import random
from pathlib import Path
from datetime import datetime, timedelta

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pyperclip
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys


class Extractor:
    def __init__(self, base_dir="data/raw/alpa",  headless=True):
        self.headless = headless
        self.base_url = "https://www.alepa.pa.gov.br/Comunicacao/Diarios"
        self.base_dir = Path(base_dir)
        self.download_dir = self.base_dir / "downloads"
        self.metadata_dir = self.base_dir / "metadata"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        chrome_options = Options()
     
        
        if self.headless:
            print("🚀 Headless mode enabled")
            chrome_options.add_argument("--headless=new")  # headless modo
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
        else:
            print("🚀 Headless mode disabled")

        chrome_options.add_argument("--log-level=3")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

    def download(self, start_date, end_date):
        self.download_range(start_date, end_date)
        print("✅ Download concluído")

    def download_range(self, start_date, end_date):
        current_date = start_date
        while current_date <= end_date:
            try:
                self.download_single(current_date)
            except Exception as e:
                print(f"⚠️ Erro ao processar {current_date.strftime('%d/%m/%Y')}: {e}")
            current_date += timedelta(days=1)
            time.sleep(random.uniform(1, 2))

    def download_single(self, day: datetime):
        print(f"📅 Buscando: {day.strftime('%d/%m/%Y')}")
        self.driver.get(self.base_url)

        sleep_time = random.uniform(1, 2)
        time.sleep(sleep_time)

        try:
            date_str = day.strftime("%d/%m/%Y")

            calendar_button = self.driver.find_element(By.ID, "dateEdit_B-1")
            calendar_button.click()

            input_field = self.wait.until(EC.presence_of_element_located((By.ID, "dateEdit_I")))
            input_field.clear()

            sleep_time = random.uniform(1, 2)

            input_field.send_keys(date_str)

            action = ActionChains(self.driver)
            action.send_keys(Keys.TAB).perform()

            sleep_time = random.uniform(1, 2)
            time.sleep(sleep_time)

            # Checa se botão aparece
            button = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Visualizar o arquivo')]")
            if not button:
                print(f"⚠️ Nenhum diário para {day.strftime('%d/%m/%Y')}")
                return

            button[0].click()
            time.sleep(4)

            # Muda para nova aba do PDF
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
                filename = f"diario-alpa-{day.isoformat()}.pdf"
                path = self.download_dir / filename
                with open(path, "wb") as f:
                    f.write(response.content)

                file_hash = hashlib.md5(response.content).hexdigest()
                self._save_metadata(url, path, day, file_hash)
                print(f"✅ Salvo: {filename} | Hash: {file_hash[:8]}")
            else:
                print(f"⚠️ Conteúdo não é PDF válido: {url}")
        except Exception as e:
            print(f"❌ Falha ao baixar PDF: {e}")

    def _save_metadata(self, url, path, date, file_hash):
        metadata = {
            "orgao": "ALEPA",
            "data_publicacao": date.isoformat(),
            "url_origem": url,
            "caminho_local": str(path),
            "data_download": datetime.now().isoformat(),
            "tamanho_bytes": os.path.getsize(path),
            "hash_md5": file_hash,
            "status": "sucesso"
        }
        
        with open(self.metadata_dir / f"metadata_{date.isoformat()}.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def close(self):
        self.driver.quit()


if __name__ == "__main__":
    extractor = Extractor()
    try:
        start = datetime(2021, 1, 1)
        end = datetime(2025, 1, 6)
        extractor.download_range(start, end)
    finally:
        extractor.close()
