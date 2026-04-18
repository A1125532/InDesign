import json
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

# print(result)

# 將結果輸出成 JSON 檔案
output_path = Path("result.json")




# 將結果轉成字典格式
result_dict = result.to_dict()

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(result_dict, f, ensure_ascii=False, indent=2)

print(f"✅ 解析完成！結果已儲存在：{output_path.absolute()}")