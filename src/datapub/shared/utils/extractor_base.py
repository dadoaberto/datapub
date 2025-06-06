import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from datapub.shared.contracts.extractor_contract import ExtractorContract


class ExtractorBase(ExtractorContract):
    def __init__(self, entity: str, base_dir: str):
        self.entity = entity
        self.base_dir = Path(base_dir)
        self.download_dir = self.base_dir / "downloads"
        self.metadata_dir = self.base_dir / "metadata"

        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def _format_date(self, date: datetime, fmt: str = "%Y-%m-%d") -> str:
        return date.strftime(fmt)

    def _save_metadata(self, data: dict, filename: str, local_path: Path, file_hash: str):
        metadata = {
            "entity": self.entity,
            "data_publicacao": data.get("data_publicacao", datetime.now().isoformat()),
            "url_origem": data.get("url_origem", ""),
            "caminho_local": str(local_path),
            "data_download": datetime.now().isoformat(),
            "tamanho_bytes": os.path.getsize(local_path),
            "hash_md5": file_hash,
            "status": "sucesso"
        }

        nome_metadata = f"metadata_{filename}.json"
        with open(self.metadata_dir / nome_metadata, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def _generate_file_hash(self, content: bytes) -> str:
        return hashlib.md5(content).hexdigest()

    def run(self):
        raise NotImplementedError("Você deve implementar o método `run`.")

    def download(self, *args, **kwargs):
        raise NotImplementedError("Você deve implementar o método `download`.")
