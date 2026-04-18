import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

from schema import ExamInput, ExamOutput
from rules import ConversionRules
from rag import ExamRAG

load_dotenv()

class ExamConverter:
    """考卷轉換主程式"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.rag = ExamRAG()
        self.rules = ConversionRules()
        # 基準目錄：app.py 所在位置
        self.base_dir = Path(__file__).resolve().parent

    def convert(self, input_data: dict, save_example: bool = False) -> dict:
        """轉換考卷"""
        # 1️⃣ 提取 OCR 文字
        content = input_data["result"]["chunks"][0]["content"]
        
        # 2️⃣ 自動分類
        #category = self.rules.detect_category(content)
        category = os.getenv("CATEGORY_OVERRIDE") or self.rules.detect_category(content)
        print(f"✓ 偵測到類別：{category}")
        
        # 3️⃣ RAG 檢索相似範例
        similar_examples = self.rag.retrieve_similar(content, category, top_k=2)
        print(f"✓ 檢索到 {len(similar_examples)} 個相似範例")
        
        # 4️⃣ 載入規則
        policy = self.rag.load_policy(category)
        
        # 5️⃣ 構建 Prompt
        system_prompt = self._build_system_prompt(similar_examples, policy)
        user_prompt = f"請將以下 OCR 辨識結果轉換為標準格式：\n\n{json.dumps(input_data, ensure_ascii=False, indent=2)}"
        
        # 6️⃣ 呼叫 GPT
        response = self.client.chat.completions.create(
            model="gpt-4o-2024-11-20",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # 7️⃣ 驗證輸出
        try:
            validated = ExamOutput(**result)
            output = validated.model_dump()
            print("✓ 輸出格式驗證通過")
        except Exception as e:
            print(f"⚠️  輸出格式驗證失敗：{e}")
            output = result

        # 8️⃣ 類別標記
        if "meta" not in output:
            output["meta"] = {}
        output["meta"]["category"] = category
        print(f"✓ 類別已設定為：{category}")

        # 9️⃣ 如果是數學考卷，標準化 bbox
        if category == "math_exam":
            output = self._standardize_math_bbox(output)
            print("✓ 已標準化數學考卷的 bbox")

        # 🔟 自動儲存（沿用原始檔名）
        self.save_as_example(input_data, output, category)
        print("✓ 已自動儲存為範例")

        print("="*60)
        print("✅ 轉換完成")
        print("="*60 + "\n")

        return output

    def _standardize_math_bbox(self, output: dict) -> dict:
        """標準化數學考卷的 bbox"""
        from bbox_generator import BBoxGenerator
        
        try:
            chunks = output["result"]["chunks"]
            all_blocks = []
            import re
            for chunk in chunks:
                for block in chunk["blocks"]:
                    match = re.search(r'\[problem\](\d+)\.', block["content"])
                    if match:
                        qnum = int(match.group(1))
                        new_bbox = BBoxGenerator.generate_bbox(qnum)
                        block["bbox"] = new_bbox
                        all_blocks.append(block)
            new_chunks = BBoxGenerator.organize_by_page(all_blocks)
            output["result"]["chunks"] = new_chunks
        except Exception as e:
            print(f"⚠️  bbox 標準化失敗：{e}")
        return output

    def _build_system_prompt(self, examples: list, policy: str) -> str:
        """構建系統提示詞"""
        prompt_path = self.base_dir / "prompt_templates" / "system.txt"
        with open(prompt_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        examples_text = ""
        for i, ex in enumerate(examples, 1):
            examples_text += f"\n### 範例 {i}\n"
            examples_text += f"**輸入：**\n```json\n{json.dumps(ex['input'], ensure_ascii=False, indent=2)[:500]}...\n```\n"
            examples_text += f"**輸出：**\n```json\n{json.dumps(ex['output'], ensure_ascii=False, indent=2)[:500]}...\n```\n"
        
        return template.format(similar_examples=examples_text, policy=policy)
    
    def save_as_example(self, input_data: dict, output_data: dict, category: str):
        """自動儲存範例（沿用原始輸入檔案名稱）"""
        # 使用絕對路徑檢查，避免誤判不存在
        examples_dir = (self.base_dir.parent / "knowledge" / category / "examples").resolve()
        if not examples_dir.exists():
            examples_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 已建立範例目錄：{examples_dir}")
        else:
            print(f"📂 範例目錄已存在：{examples_dir}")

        # 嘗試從 meta 或 file 欄位取得原始檔名
        input_name = input_data.get("meta", {}).get("source_filename", None)
        if not input_name:
            input_name = input_data.get("file", "unnamed")
        base_name = Path(input_name).stem

        # 設定輸入與輸出檔案名稱
        input_file = examples_dir / f"{base_name}_input.json"
        output_file = examples_dir / f"{base_name}_output.json"

        # 寫入檔案
        with open(input_file, 'w', encoding='utf-8') as f:
            json.dump(input_data, f, ensure_ascii=False, indent=2)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

        print(f"✓ 已儲存為範例：{base_name}_input.json / {base_name}_output.json")

# CLI 使用
if __name__ == "__main__":
    import sys
    converter = ExamConverter()
    base_dir = Path(__file__).resolve().parent
    default_input = base_dir.parent / "knowledge" / "math_exam" / "examples" / "ex1_input.json"
    input_file = Path(sys.argv[1]) if len(sys.argv) > 1 else default_input

    with open(input_file, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    # 將輸入檔案名稱記錄進 meta，供儲存時使用
    if "meta" not in input_data:
        input_data["meta"] = {}
    input_data["meta"]["source_filename"] = input_file.name

    output = converter.convert(input_data)
    print("\n" + "="*50)
    print("轉換結果：")
    print(json.dumps(output, ensure_ascii=False, indent=2))
