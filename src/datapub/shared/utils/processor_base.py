from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import datapub.shared.contracts.extractor_contract as ExtractorContract

class ProcessorBase(ABC):
    def __init__(self, entity: str, processor_type: str, base_dir: str):
        self.entity = entity
        self.processor_type = processor_type
        self.base_dir = Path(base_dir)
        self.output_dir = self.base_dir
        
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def extract_text(self, file_path: Path) -> Optional[str]:
        pass
    
    @staticmethod
    def add_arguments(parser):
        raise NotImplementedError("You must implement `add_arguments` method in the child class.")

    def process(self, *args, **kwargs):
        raise NotImplementedError("You must implement `download` method in the child class.")
