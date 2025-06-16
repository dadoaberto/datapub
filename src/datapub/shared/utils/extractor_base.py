import os
import json
import hashlib
from pathlib import Path
from datetime import datetime
from datapub.shared.contracts.extractor_contract import ExtractorContract


class ExtractorBase(ExtractorContract):
    def __init__(self, entity: str, base_dir: str, extractor_type: str, headless=True):
        self.entity = entity
        self.extractor_type = extractor_type
        self.headless = headless
        self.base_dir = Path(base_dir)
        self.downloads_dir = self.base_dir / "downloads"
        self.metadata_dir = self.base_dir / "metadata"
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def _format_date(self, date: datetime, fmt: str = "%Y-%m-%d") -> str:
        return date.strftime(fmt)

    def _save_metadata(self, file_name, file_url, file_path, file_type, hash):
        metadata = {
            "entity": self.entity,
            "type": self.extractor_type,
            "filename": file_name,
            "url": file_url,
            "source": self.base_url,
            "path": str(file_path),
            "file_type": file_type,
            "file_size": os.path.getsize(file_path),
            "hash_md5": hash,
            "status": "success",
            "download_at": datetime.now().isoformat(),
        }

        name_metadata = f"metadata_{file_name}.json"
        with open(self.metadata_dir / name_metadata, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    @staticmethod
    def add_arguments(parser):
        raise NotImplementedError("You must implement `add_arguments` method in the child class.")

    def download(self, *args, **kwargs):
        raise NotImplementedError("You must implement `download` method in the child class.")
