
# ───────────────────────────────
# File: cli.py
# ───────────────────────────────
import argparse
from core.scanner import scan_and_generate_tests
parser = argparse.ArgumentParser()
parser.add_argument("--model", choices=["chatgpt", "claude", "gemini"], required=True)
parser.add_argument("--src", default="src")
parser.add_argument("--out", default="tests/Generated")
parser.add_argument("--mode", choices=["text", "file"], default="text")
args = parser.parse_args()

if args.model == "chatgpt":
    from openai import OpenAI
    from adapters.chatgpt import ChatGPTAdapter
    adapter = ChatGPTAdapter(OpenAI(api_key="your-openai-key"), assistant_id="your-assistant-id")

elif args.model == "claude":
    import anthropic
    from adapters.claude import ClaudeAdapter
    adapter = ClaudeAdapter(anthropic.Anthropic(api_key="your-anthropic-key"))

elif args.model == "gemini":
    import google.generativeai as genai
    from adapters.gemini import GeminiAdapter
    genai.configure(api_key="your-gemini-key")
    adapter = GeminiAdapter(genai.GenerativeModel("gemini-pro"))

scan_and_generate_tests(args.src, args.out, adapter, mode=args.mode)