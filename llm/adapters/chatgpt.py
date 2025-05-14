from llm.base import LLMAdapter
from llm.core.prompt import PROMPT
import os
class ChatGPTAdapter(LLMAdapter):
    def __init__(self, client, assistant_id=None):
        self.client = client
        self.assistant_id = assistant_id

    def generate_test_case(self, source_code: str, filename: str) -> str:
        prompt = (
            f"Saya punya file PHP `{filename}` berikut:\n"
            f"```php\n{source_code}\n```\n"
            f"{PROMPT}"
        )
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Kamu adalah pengembang PHP dan penulis test profesional."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content

    def generate_test_case_from_file(self, source_path: str, output_dir: str) -> str:
        file = self.client.files.create(file=open(source_path, "rb"), purpose="assistants")

        thread = self.client.beta.threads.create()
        self.client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=PROMPT,
            file_ids=[file.id]
        )

        run = self.client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=self.assistant_id
        )

        while True:
            run_status = self.client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status == "completed":
                break

        messages = self.client.beta.threads.messages.list(thread_id=thread.id)
        for message in reversed(messages.data):
            for file_id in message.file_ids:
                result = self.client.files.retrieve_content(file_id)
                filename = os.path.basename(source_path).replace(".php", "Test.php")
                path = os.path.join(output_dir, filename)
                with open(path, "w") as f:
                    f.write(result)
                return path