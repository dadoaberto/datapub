# src/downloaders/alepa.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta
from pathlib import Path
import time
import os
import hashlib
import json

class Downloader:
    def __init__(self, base_dir="data/raw/ale_pa", headless=True):
        self.base_url = "https://www.alepa.pa.gov.br/Comunicacao/Diarios"
        self.base_dir = Path(base_dir)
        self.download_dir = self.base_dir / "downloads"
        self.metadata_dir = self.base_dir / "metadata"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        chrome_options = Options()
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)

        if headless:
            chrome_options.add_argument("--headless=new")  # headless modo
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")

    def download(self, start_date=None, end_date=None):
        self.download_range(start_date, end_date)
        print("✅ Download concluido")

    def download_range(self, start_date, end_date):
        current_date = start_date
        while current_date <= end_date:
            self.download_single(current_date)
            current_date += timedelta(days=1)

    def download_single(self, day: datetime):
        print(f"🗓 Buscando: {day.strftime('%d/%m/%Y')}")
        self.driver.get(self.base_url)

        # Espera o campo de data
        try:
            input_field = self.wait.until(EC.presence_of_element_located((By.ID, "dateEdit_I")))
            input_field.clear()
            input_field.send_keys(day.strftime("%d/%m/%Y"))
            input_field.send_keys("\n")  # força o onchange

            time.sleep(3)

            # Verifica se existe botão de visualizar
            button = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Visualizar o arquivo')]")
            if not button:
                print(f"⚠️ Nenhum diário para {day.strftime('%d/%m/%Y')}")
                return

            button[0].click()
            time.sleep(3)

            # Nova aba com PDF
            self.driver.switch_to.window(self.driver.window_handles[-1])
            pdf_url = self.driver.current_url
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

            self._download_pdf(pdf_url, day)

        except Exception as e:
            print(f"❌ Erro em {day.strftime('%d/%m/%Y')}: {e}")

    def _download_pdf(self, url, day):
        import requests
        response = requests.get(url)
        if response.status_code == 200 and b"%PDF" in response.content[:10]:
            filename = f"alepa-{day.isoformat()}.pdf"
            path = self.download_dir / filename
            with open(path, "wb") as f:
                f.write(response.content)

            file_hash = hashlib.md5(response.content).hexdigest()
            self._save_metadata(url, path, day, file_hash)
            print(f"✅ Salvo: {filename} | Hash: {file_hash[:8]}")
        else:
            print(f"⚠️ PDF inválido ou não encontrado em {url}")

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
    downloader = Downloader()
    start = datetime(2024, 12, 10)
    end = datetime(2024, 12, 15)
    downloader.download_range(start, end)
    downloader.close()
