import os

# Settings has no defaults for these two fields, and main.py constructs a
# real aiogram Bot + RagClient at import time -- set dummy values before any
# test module imports app/main code, so collection doesn't fail or try to
# reach a real Telegram token / RAG service.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456789:TEST-TOKEN-not-a-real-bot-xxxxxxxx")
os.environ.setdefault("RAG_BASE_URL", "http://rag.testing")
