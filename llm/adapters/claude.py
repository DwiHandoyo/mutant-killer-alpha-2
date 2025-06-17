from llm.base import LLMAdapter
import os
from llm.core.prompt import get_prompt
import os
class ClaudeAdapter(LLMAdapter):
    def __init__(self, client, infection_result={}):
        self.client = client
        self.infection_result = infection_result

    def generate_test_case(self, source_code: str, filename: str) -> str:
        PROMPT = get_prompt()
        if len(self.infection_result.values()):
            if filename in self.infection_result:
                
                PROMPT += f"\n{source_code}\n\n"
                PROMPT += f"\nperhatikan infection result berikut pada 'escaped' dan 'uncovered'. Escaped adalah mutant yang tidak berhasil ter-kill dan uncovered adalah yang tidak ada test casenya. Pada tiap element di escaped dan uncovered ada startLine yang menandakan line yang dilakukan mutation"
                PROMPT += f"\n\nInfection result: {self.infection_result[filename]}"
            else:
                return 
        prompt = (
            f"Human: Berikut file PHP `{filename}`:\n"
            f"\n{source_code}\n\n"
            f"{PROMPT}"
        )
        response = self.client.messages.create(
            model="claude-3-opus-20240229",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )
        return response.content[0].text

    def generate_test_case_from_file(self, source_path: str, output_dir: str) -> str:
        PROMPT = get_prompt()
        sanitized_name = os.path.basename(source_path)
        if len(self.infection_result.values()):
            if sanitized_name in self.infection_result:
                PROMPT += f"\nperhatikan infection result berikut pada 'escaped' dan 'uncovered'. Escaped adalah mutant yang tidak berhasil ter-kill dan uncovered adalah yang tidak ada test casenya. Pada tiap element di escaped dan uncovered ada startLine yang menandakan line yang dilakukan mutation"
                PROMPT += f"\n\nInfection result: {self.infection_result[sanitized_name]}"
            else:
                return 
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
            out.write(response.content[0].text.replace("```php", "").replace("```", ""))
        return output_path