import requests
from pathlib import Path
import hashlib
from datetime import datetime, timedelta
import json

class ESTADOSPDownloader:
    def __init__(self, base_path="data/raw/estado_sp"):
        self.base_path = Path(base_path)
        self.orgao_path = self.base_path / "estado_sp"
        self.downloads_path = self.orgao_path / "downloads"
        self.downloads_path.mkdir(parents=True, exist_ok=True)
        
    def download_diarios(self, start_date, end_date):
        """Baixa diários no intervalo de datas"""
        current_date = start_date
        while current_date <= end_date:
            url = self._generate_url(current_date)
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    file_hash = hashlib.md5(response.content).hexdigest()
                    filename = f"diario_{current_date.strftime('%Y-%m-%d')}_{file_hash[:8]}.pdf"
                    filepath = self.downloads_path / filename
                    
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    # Registrar metadados
                    self._save_metadata(filepath, current_date, url)
            except Exception as e:
                print(f"Erro ao baixar {url}: {str(e)}")
            current_date += timedelta(days=1)
    
    def _generate_url(self, date):
        """Lógica específica para gerar URL do diário"""
        return f"http://www.diariooficial.sp.gov.br/xml/{date.year}/{date.month:02d}/do{date.day:02d}{date.month:02d}{date.year}.pdf"
    
    def _save_metadata(self, filepath, date, url):
        """Salva metadados em arquivo JSON"""
        metadata = {
            "orgao": "estado_sp",
            "data_publicacao": date.isoformat(),
            "url_origem": url,
            "caminho_local": str(filepath),
            "data_download": datetime.now().isoformat(),
            "tamanho": filepath.stat().st_size
        }
        
        metadata_path = self.downloads_path / f"{filepath.stem}_meta.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
