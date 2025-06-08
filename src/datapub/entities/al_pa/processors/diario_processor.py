from pathlib import Path
from typing import Optional
import json
import argparse
import dateparser
from datetime import datetime, timedelta, date
import pdfplumber
import re
import pytesseract
from PIL import ImageOps

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

        filtered_files = []

        for file in sorted(self.metadata_dir.glob('*.json'), key=lambda f: f.name):
            with open(file, "r", encoding="utf-8") as f_in:
                metadata = json.load(f_in)
                file_path = Path(metadata["path"])

                match = re.search(r"(\d{4}-\d{2}-\d{2})(?:_(\d{4}-\d{2}-\d{2}))?", file_path.name)
                if not match:
                    continue

                file_start_str = match.group(1)
                file_end_str = match.group(2) or file_start_str

                try:
                    file_start_date = datetime.fromisoformat(file_start_str).date()
                    file_end_date = datetime.fromisoformat(file_end_str).date()
                except ValueError:
                    continue

                if file_end_date >= start_date and file_start_date <= end_date:
                    filtered_files.append(file)

        for file in filtered_files:
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
        print(f"📦 Processando: {file_path.name}")
        if file_path.suffix.lower() != '.pdf':
            return None

        text_content = []

        with pdfplumber.open(file_path) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                page_image = page.to_image(resolution=300).original.convert("L")  # escala de cinza
                page_image = ImageOps.autocontrast(page_image)

                # Executar OCR na imagem
                ocr_text = pytesseract.image_to_string(page_image, lang='por')  # idioma português
                print(f"🧠 OCR extraído da página {idx} de {file_path.name}")
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