from llm.base import LLMAdapter
import os
from llm.core.prompt import PROMPT
import os

class ClaudeAdapter(LLMAdapter):
    def __init__(self, client):
        self.client = client

    def generate_test_case(self, source_code: str, filename: str) -> str:
        prompt = (
            f"Human: Berikut file PHP `{filename}`:\n"
            f"```php\n{source_code}\n```\n"
            f"{PROMPT}"
        )
        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )
        return response.content[0].text

    def generate_test_case_from_file(self, source_path: str, output_dir: str) -> str:
        with open(source_path, "r") as f:
            content = f.read()

        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": PROMPT},
                        {"type": "file", "file": self.client.files.create(file=open(source_path, "rb"))}
                    ]
                }
            ]
        )

        filename = os.path.basename(source_path).replace(".php", "Test.php")
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w") as out:
            out.write(response.content[0].text)
        return output_path