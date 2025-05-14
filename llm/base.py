from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    @abstractmethod
    def generate_test_case(self, source_code: str, filename: str) -> str:
        pass

    @abstractmethod
    def generate_test_case_from_file(self, source_path: str, output_dir: str) -> str:
        pass
