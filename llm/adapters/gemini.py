from llm.base import LLMAdapter
from llm.core.prompt import PROMPT
import os

class GeminiAdapter(LLMAdapter):
    def __init__(self, model):
        self.model = model

    def generate_test_case(self, source_code: str, filename: str) -> str:
        prompt = (
            PROMPT
        )
        response = self.model.generate_content(prompt)
        return response.text

    def generate_test_case_from_file(self, source_path: str, output_dir: str) -> str:
        with open(source_path, "r") as f:
            php_code = f.read()

        response = self.model.generate_content(
            contents=[{"role": "user", "parts": [PROMPT, {"text": php_code}]}]
        )

        filename = os.path.basename(source_path).replace(".php", "Test.php")
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w") as out:
            out.write(response.text)
        return output_path
