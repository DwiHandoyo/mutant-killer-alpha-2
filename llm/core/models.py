import os
# importing necessary functions from dotenv library
from dotenv import load_dotenv, dotenv_values 
# loading variables from .env file
load_dotenv() 

# accessing and printing value
print(os.getenv("MY_KEY"))
def model_factory(model_name):
    if model_name == "chatgpt":
        from openai import OpenAI
        from llm.adapters.chatgpt import ChatGPTAdapter
        return ChatGPTAdapter(OpenAI(api_key=os.getenv("OPENAI_API_KEY")))

    elif model_name == "claude":
        import anthropic
        from llm.adapters.claude import ClaudeAdapter
        return ClaudeAdapter(anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY")))

    elif model_name == "gemini":
        import google.generativeai as genai
        from llm.adapters.gemini import GeminiAdapter
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        return GeminiAdapter(genai.GenerativeModel("gemini-pro"))

    else:
        raise ValueError(f"Unknown model: {model_name}")
