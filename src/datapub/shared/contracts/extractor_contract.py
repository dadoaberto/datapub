from abc import ABC, abstractmethod

class ExtractorContract(ABC):
    @abstractmethod
    def download(self, *args, **kwargs):
        pass

    @abstractmethod
    def add_arguments(self):
        pass