from abc import ABC, abstractmethod

class ExtractorContract(ABC):
    @abstractmethod
    def download(self, *args, **kwargs):
        """Realiza o download dos dados brutos."""
        pass
