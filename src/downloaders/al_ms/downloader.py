from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import os
import hashlib
import json
from pathlib import Path
from datetime import datetime
from pathlib import Path
from datetime import datetime, timedelta

class Downloader:
    def __init__(self, base_dir="data/raw/alms", headless=True):
        self.base_dir = Path(base_dir)
        self.downloads_dir = (self.base_dir / "downloads").resolve()
        self.metadata_dir = self.base_dir / "metadata"
        self.logs_dir = self.base_dir / "logs"
        
        self.headless = headless
        
        # Cria os diretórios se não existirem
        # self.downloads_dir.mkdir(parents=True, exist_ok=True)
        os.makedirs(self.downloads_dir, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Configurações do navegador
        self._setup_driver()
        
        # Configurações da busca
        self.start_number = 1  # Número inicial do diário
        self.max_attempts = 2  # Tentativas por diário
        self.delay_between = 1  # Delay entre requisições
        self.max_consecutive_failures = 5  # Limite de falhas consecutivas
    
    def _setup_driver(self):
        """Configura o WebDriver do Chrome"""
        chrome_options = webdriver.ChromeOptions()
        
        # Configurações de download
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": str(self.downloads_dir),
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True,
            "download.directory_upgrade": True,
        })
        
        if self.headless:
            chrome_options.add_argument("--headless=new")  # headless modo
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
        
        # Configura o serviço do Chrome
        service = Service(ChromeDriverManager().install())
        
        # Inicia o navegador
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)

    def download(self, start_num=None, end_num=None):
        """Baixa diários em um intervalo numérico"""
        self.download_range(start_num, end_num)
        print("✅ Download concluido")
    
    def download_range(self, start_num=None, end_num=None):
        """Baixa diários em um intervalo numérico"""
        current_num = start_num or self.start_number
        end_num = end_num or float('inf')
        consecutive_failures = 0
        
        self._log_start()
        
        try:
            self.driver.get("https://diariooficial.al.ms.gov.br/")
            
            while current_num <= end_num:
                num_str = str(current_num).zfill(4)
                success = self._process_diario(num_str)
                
                if not success:
                    consecutive_failures += 1
                    if consecutive_failures >= self.max_consecutive_failures:
                        print(f"🚧 {self.max_consecutive_failures} falhas consecutivas, encerrando...")
                        break
                else:
                    consecutive_failures = 0
                
                current_num += 1
                time.sleep(self.delay_between)
        
        finally:
            self._cleanup()
    
    def _process_diario(self, num_str):
        """Processa um diário específico"""
        for attempt in range(self.max_attempts):
            try:
                print(f"🔍 Tentando Diário nº {num_str} (tentativa {attempt + 1})")
                
                # Preenche e submete o formulário de busca
                input_field = self.wait.until(EC.presence_of_element_located((By.ID, "pesquisa")))
                input_field.clear()
                input_field.send_keys(num_str)
                
                search_btn = self.driver.find_element(By.ID, "filtro")
                search_btn.click()

                # Aguarda a tabela de resultados atualizar
                time.sleep(1)

                # Tenta localizar a tabela de resultados
                try:
                    tabela = self.driver.find_element(By.CSS_SELECTOR, "table.table")
                    linhas = tabela.find_elements(By.TAG_NAME, "tr")

                    if len(linhas) > 1:
                        # Percorre todas as linhas a partir da segunda, tentando achar o link de download
                        for linha in linhas[1:]:
                            links = linha.find_elements(By.TAG_NAME, "a")
                            if not links:
                                continue  # pula se não tiver link

                            link_download = links[-1]  # pega o último link (download)
                            href = link_download.get_attribute("href")
                            if href:
                                print(f"📥 Baixando PDF: {href}")
                                if self._download_pdf(num_str, href):
                                    return True  # sucesso, retorna True
                                else:
                                    print(f"⚠️ Falha no download do PDF para o número {num_str}")
                            else:
                                print(f"⚠️ Link de download vazio para o número {num_str}")
                        # Se não baixou nenhum, retorna False
                        print(f"🚫 Nenhum PDF baixado para o número {num_str}")
                        return False
                    else:
                        print(f"🚫 Diário nº {num_str} não encontrado.")
                        return False

                except Exception as e:
                    print(f"❌ Nenhuma tabela encontrada para nº {num_str}: {str(e)}")
                    return False
                    
            except Exception as e:
                print(f"⚠️ Erro na tentativa {attempt + 1} para {num_str}: {str(e)}")
                if attempt == self.max_attempts - 1:
                    self._log_error(num_str, str(e))
                time.sleep(1)
        
        return False
    
    def _download_pdf(self, num_str, pdf_url):
        """Baixa e processa um PDF individual com tratamento robusto de erros"""
        try:
            print(f"⏳ Iniciando download do Diário {num_str}...")

            # Abre o PDF em nova aba
            self.driver.execute_script("window.open(arguments[0], '_blank');", pdf_url)

            # Aguarda o download com timeout
            max_wait_time = 30  # segundos
            start_time = time.time()
            downloaded = False
            initial_files = set(self.downloads_dir.glob("*.pdf"))

            while (time.time() - start_time) < max_wait_time:
                current_files = set(f for f in self.downloads_dir.glob("*.pdf") if not f.name.endswith('.crdownload'))
                new_files = current_files - initial_files

                if new_files:
                    # Assume o arquivo mais recente como o novo
                    latest_file = max(new_files, key=lambda f: f.stat().st_mtime)

                    # Verifica se o download está completo (tamanho estável por 2s)
                    initial_size = latest_file.stat().st_size
                    time.sleep(2)
                    if latest_file.stat().st_size == initial_size:
                        downloaded = True
                        break
                time.sleep(1)

            if not downloaded:
                print(f"❌ Timeout ao baixar Diário {num_str}")
                self._log_error(num_str, "Timeout no download")
                return False

            # Verifica se é um PDF válido
            try:
                with latest_file.open('rb') as f:
                    if not f.read(4).startswith(b'%PDF'):
                        print(f"❌ Arquivo inválido para Diário {num_str}")
                        latest_file.unlink(missing_ok=True)
                        self._log_error(num_str, "Arquivo PDF inválido")
                        return False
            except Exception as e:
                print(f"❌ Erro ao verificar PDF do Diário {num_str}: {str(e)}")
                self._log_error(num_str, f"Erro de leitura do arquivo: {str(e)}")
                return False

            # Gera nome único para o arquivo
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                new_filename = f"diario-alms-{num_str}_{timestamp}.pdf"
                new_path = self.downloads_dir / new_filename

                if new_path.exists():
                    new_filename = f"diario-alms-{num_str}_{timestamp}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:4]}.pdf"
                    new_path = self.downloads_dir / new_filename

                latest_file.rename(new_path)
            except Exception as e:
                print(f"❌ Erro ao renomear arquivo do Diário {num_str}: {str(e)}")
                self._log_error(num_str, f"Erro ao renomear arquivo: {str(e)}")
                return False

            # Salva metadados
            try:
                file_size = new_path.stat().st_size
                if file_size == 0:
                    print(f"❌ Arquivo vazio para Diário {num_str}")
                    new_path.unlink(missing_ok=True)
                    return False

                self._save_metadata(num_str, pdf_url, new_path)
                print(f"✅ Diário {num_str} baixado com sucesso ({file_size/1024:.2f} KB): {new_filename}")
                return True

            except Exception as e:
                print(f"❌ Erro ao salvar metadados do Diário {num_str}: {str(e)}")
                new_path.unlink(missing_ok=True)
                return False

        except Exception as e:
            print(f"❌ Erro ao baixar Diário {num_str}: {str(e)}")
            self._log_error(num_str, str(e))
            return False
  
    def _save_metadata(self, num_str, url, filepath):
        """Salva metadados do download"""
        metadata = {
            "orgao": "MS",
            "numero_diario": num_str,
            "url_origem": url,
            "caminho_local": str(filepath),
            "data_download": datetime.now().isoformat(),
            "tamanho_bytes": os.path.getsize(filepath),
            "hash_md5": self._calculate_hash(filepath),
            "status": "sucesso"
        }
        
        metadata_path = self.metadata_dir / f"metadata_{num_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    def _calculate_hash(self, filepath):
        """Calcula hash MD5 do arquivo"""
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _log_start(self):
        """Registra início do processo"""
        log_entry = {
            "inicio": datetime.now().isoformat(),
            "start_number": self.start_number,
            "config": {
                "max_attempts": self.max_attempts,
                "delay": self.delay_between,
                "max_consecutive_failures": self.max_consecutive_failures
            }
        }
        
        log_path = self.logs_dir / f"execucao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log_entry, f, ensure_ascii=False, indent=2)
    
    def _log_error(self, num_str, error_msg):
        """Registras erros ocorridos"""
        error_log = {
            "numero_diario": num_str,
            "data_hora": datetime.now().isoformat(),
            "erro": error_msg
        }
        
        error_path = self.logs_dir / "erros.json"
        with open(error_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(error_log, ensure_ascii=False) + "\n")
    
    def _cleanup(self):
        """Finaliza o navegador"""
        if hasattr(self, 'driver'):
            self.driver.quit()

    def get_recent_complete_pdfs(download_dir: Path, since: float = 60.0) -> set[Path]:
        """Retorna arquivos PDF completos, excluindo temporários e antigos."""
        now = datetime.now()
        pdfs = set()

        for file in download_dir.iterdir():
            if not file.name.lower().endswith(".pdf"):
                continue
            if file.name.endswith(".crdownload") or file.name.startswith("~"):
                continue  # arquivo ainda em download ou temporário
            try:
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                if (now - mtime).total_seconds() <= since:
                    pdfs.add(file)
            except Exception:
                continue  # em caso de falha ao acessar stats

        return pdfs

if __name__ == "__main__":
    downloader = Downloader()
    downloader.download_range()
