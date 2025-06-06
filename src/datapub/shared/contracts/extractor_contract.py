from abc import ABC, abstractmethod

class ExtractorContract(ABC):
    @abstractmethod
    def run(self):
        """Executa o processo completo de extração."""
        pass

    @abstractmethod
    def download(self, *args, **kwargs):
        """Realiza o download dos dados brutos."""
        pass
