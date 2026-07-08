"""Dummy env so importing settings-backed modules works without a real .env."""
import os

os.environ.setdefault("BOT_TOKEN", "123456:test-token")
os.environ.setdefault("ADMIN_IDS", "1")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
