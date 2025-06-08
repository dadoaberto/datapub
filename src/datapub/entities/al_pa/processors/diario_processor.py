from pathlib import Path
from typing import Optional
import json
import argparse
import dateparser
from datetime import datetime, timedelta, date
import pdfplumber
import pytesseract

from datapub.shared.utils.processor_base import ProcessorBase

class ALPAProcessor(ProcessorBase):
    def __init__(self, entity="ALPA", processor_type="diario", base_dir="storage/processed/al_pa"):
        super().__init__(entity=entity, base_dir=Path(base_dir), processor_type=processor_type)
        self.metadata_dir = Path("storage/raw/al_pa/metadata")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        parser.add_argument("--start", help="Data inicial no formato YYYY-MM-DD")
        parser.add_argument("--end", help="Data final no formato YYYY-MM-DD")

    def process(self, start=None, end=None):
        start_date = dateparser.parse(start).date() if start else date(2021, 1, 1)
        end_date = dateparser.parse(end).date() if end else date.today()

        files = sorted(self.metadata_dir.glob('*.json'), key=lambda f: f.name)

        for file in files:
            with open(file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                file_path = Path(metadata["path"])
                output_file = self.output_dir / f"{file_path.stem}.txt"

                if output_file.exists():
                    print(f"📦 Já existe: {output_file.name}, pulando extração.")
                    continue

                result = self.extract_text(file_path)
                if result is not None:
                    self._save_result(file_path, result)

    def extract_text(self, file_path: Path) -> Optional[str]:
        if file_path.suffix.lower() != '.pdf':
            return None

        text_content = []

        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)
                else:
                    page_image = page.to_image(resolution=300).original
                    ocr_text = pytesseract.image_to_string(page_image)
                    text_content.append(ocr_text)

        return "\n".join(text_content)

    def _save_result(self, file_path: Path, text_content: str):
        output_file = self.output_dir / f"{file_path.stem}.txt"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text_content)

def main():
    processor = ALPAProcessor()
    processor.process()
    print("✅ Extração concluída com sucesso!")

if __name__ == "__main__":
    main()
