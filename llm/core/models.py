import os
# importing necessary functions from dotenv library
from dotenv import load_dotenv, dotenv_values 
# loading variables from .env file
load_dotenv() 

# accessing and printing value
def model_factory(model_name, infection_result={}):
    if model_name == "chatgpt":
        from openai import OpenAI
        from llm.adapters.chatgpt import ChatGPTAdapter
        assistant_id = os.getenv("ASSISTANT_ID", '')
        return ChatGPTAdapter(OpenAI(api_key=os.getenv("OPENAI_API_KEY")), assistant_id, infection_result)

    elif model_name == "claude":
        import anthropic
        from llm.adapters.claude import ClaudeAdapter
        return ClaudeAdapter(anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY")), infection_result)

    elif model_name == "gemini":
        import google.generativeai as genai
        from llm.adapters.gemini import GeminiAdapter
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        return GeminiAdapter(genai.GenerativeModel("gemini-2.0-flash"), infection_result)

    else:
        raise ValueError(f"Unknown model: {model_name}")
