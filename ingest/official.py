import os
from pathlib import Path

import convert_env  # noqa: F401 — 載入 convert/server/.env
from reducto import Reducto

api_key = os.getenv("REDUCTO_API_KEY")
if not api_key:
    raise SystemExit("未設定 REDUCTO_API_KEY（請在 convert/server/.env 設定）")

client = Reducto(api_key=api_key)
upload = client.upload(file=Path("123.pdf"))
result = client.parse.run(input=upload)

print(result)