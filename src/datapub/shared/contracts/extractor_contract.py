from abc import ABC, abstractmethod

class ExtractorContract(ABC):
    def download(self, *args, **kwargs):
        pass

    @abstractmethod
    def add_arguments():
        pass