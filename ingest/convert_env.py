"""載入與 convert 後端共用的 `convert/server/.env`（OpenAI、Reducto 等）。"""
from pathlib import Path

from dotenv import load_dotenv

_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / "convert" / "server" / ".env")
