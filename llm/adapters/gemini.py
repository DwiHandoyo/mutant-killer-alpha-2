from llm.base import LLMAdapter
from llm.core.prompt import get_prompt
import os

class GeminiAdapter(LLMAdapter):
    def __init__(self, model, infection_result={}):
        self.model = model
        self.infection_result = infection_result

    def generate_test_case(self, source_code: str, filename: str, iteration_error: str = None) -> str:
        PROMPT = get_prompt()
        if len(self.infection_result.values()):
            if filename in self.infection_result:
                
                PROMPT += f"\n{source_code}\n\n"
                PROMPT += f"\nperhatikan infection result berikut pada 'escaped' dan 'uncovered'. Escaped adalah mutant yang tidak berhasil ter-kill dan uncovered adalah yang tidak ada test casenya. Pada tiap element di escaped dan uncovered ada startLine yang menandakan line yang dilakukan mutation"
                PROMPT += f"\n\nInfection result: {self.infection_result[filename]}"
            else:
                return 
        
        if iteration_error:
            PROMPT += f"\n\nPerhatikan juga error berikut yang terjadi pada iterasi sebelumnya: {iteration_error}"
        prompt = (
            PROMPT
        )
        response = self.model.generate_content(prompt)
        return response.text

    def generate_test_case_from_file(self, source_path: str, output_dir: str, iteration_error: str = None) -> str:
        PROMPT = get_prompt()
        sanitized_name = os.path.basename(source_path)
        with open(source_path, "r") as f:
            php_code = f.read()

        if len(self.infection_result.values()):
            if sanitized_name in self.infection_result:
                PROMPT += f"\nperhatikan infection result berikut pada 'escaped' dan 'uncovered'. Escaped adalah mutant yang tidak berhasil ter-kill dan uncovered adalah yang tidak ada test casenya. Pada tiap element di escaped dan uncovered ada startLine yang menandakan line yang dilakukan mutation"
                PROMPT += f"\n\nInfection result: {self.infection_result[sanitized_name]}"
            else:
                return 

        if iteration_error:
            PROMPT += f"\n\nPerhatikan juga error berikut yang terjadi pada iterasi sebelumnya: {iteration_error}"

        response = self.model.generate_content(
            contents=[{"role": "user", "parts": [PROMPT, {"text": php_code}]}]
        )

        response_trim =  trim_response(response.text)
        filename = os.path.basename(source_path).replace(".php", "Test.php")
        output_path = os.path.join(output_dir, filename)
        with open(output_path, "w") as out:
            out.write(response_trim)
        return output_path

def trim_response(response):
    """
    Trim the response to remove unnecessary parts.
    """
    trim_response = response.replace("```php", "").replace("```", "").strip()
    namespace_index = trim_response.find("namespace")
    if namespace_index != -1:
        trim_response = trim_response[:namespace_index].replace("\n\n", "\n") + trim_response[namespace_index:]
    return trim_response