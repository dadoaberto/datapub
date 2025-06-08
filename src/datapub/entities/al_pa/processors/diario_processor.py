from pathlib import Path
from typing import Optional, Type
import json
import argparse
import pdfplumber
import pytesseract

from datapub.shared.utils.processor_base import ProcessorBase

class ALPAProcessor(ProcessorBase):
  
    def __init__(self, entity="ALPA", processor_type="diario", base_dir="storage/processed/al_pa"):
        super().__init__(entity=entity, base_dir=base_dir, processor_type=processor_type)
        self.metadata_dir = Path("storage/raw/al_pa/metadata")

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        parser.add_argument("--start", help="Data inicial no formato YYYY-MM-DD")
        parser.add_argument("--end", help="Data final no formato YYYY-MM-DD")

    def process(self):
        for file in self.metadata_dir.iterdir():
            if file.suffix == '.json':
                with open(file, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    result = self.extract_text(Path(metadata["path"]))
                    if result:
                        self._save_result(metadata["path"], result)

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
                    # OCR com Tesseract
                    page_image = page.to_image(resolution=300).original
                    ocr_text = pytesseract.image_to_string(page_image)
                    text_content.append(ocr_text)

        return "\n".join(text_content)

    def _save_result(self, original_path: str, text_content: str):
        original_file = Path(original_path)
        output_file = self.output_dir / f"{original_file.stem}.txt"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text_content)


def main():
    processor = ALPAProcessor()
    processor.process()
    print("Extração concluída com sucesso!")


if __name__ == "__main__":
    main()
