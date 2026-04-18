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
        
    def convert(self, input_data: dict, save_example: bool = False) -> dict:
        """
        轉換考卷
        
        Args:
            input_data: Reducto OCR 輸出
            
        Returns:
            標準化的考卷 JSON
        """
        # 1. 提取 OCR 文字
        content = input_data["result"]["chunks"][0]["content"]
        
        # 2. 自動分類
        category = self.rules.detect_category(content)
        print(f"✓ 偵測到類別：{category}")
        
        # 3. RAG 檢索相似範例
        similar_examples = self.rag.retrieve_similar(content, category, top_k=2)
        print(f"✓ 檢索到 {len(similar_examples)} 個相似範例")
        
        # 4. 載入規則
        policy = self.rag.load_policy(category)
        
        # 5. 構建 Prompt
        system_prompt = self._build_system_prompt(similar_examples, policy)
        user_prompt = f"請將以下 OCR 辨識結果轉換為標準格式：\n\n{json.dumps(input_data, ensure_ascii=False, indent=2)}"
        
        # 6. 呼叫 GPT
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
        
        # 7. 驗證輸出
        try:
            validated = ExamOutput(**result)
            output = validated.model_dump()
            print("✓ 輸出格式驗證通過")
        except Exception as e:
            print(f"⚠️  輸出格式驗證失敗：{e}")
            output = result

        # 🔧 強制使用偵測到的類別
        if "meta" not in output:
            output["meta"] = {}
        output["meta"]["category"] = category
        print(f"✓ 類別已設定為：{category}")

        # 🔧 如果是數學考卷，標準化 bbox
        if category == "math_exam":
            output = self._standardize_math_bbox(output)
            print("✓ 已標準化數學考卷的 bbox")

        # 8. 儲存範例（可選）
        if save_example:
            self.save_as_example(input_data, output, category)
            print("✓ 已儲存為範例")

        print("="*60)
        print("✅ 轉換完成")
        print("="*60 + "\n")

        return output

    def _standardize_math_bbox(self, output: dict) -> dict:
        """
        標準化數學考卷的 bbox
        
        Args:
            output: 轉換後的輸出
            
        Returns:
            bbox 標準化後的輸出
        """
        from bbox_generator import BBoxGenerator
        
        try:
            chunks = output["result"]["chunks"]
            all_blocks = []
            
            # 收集所有 blocks 並提取題號
            for chunk in chunks:
                for block in chunk["blocks"]:
                    # 從 content 提取題號
                    import re
                    match = re.search(r'\[problem\](\d+)\.', block["content"])
                    if match:
                        question_number = int(match.group(1))
                        
                        # 生成標準 bbox
                        new_bbox = BBoxGenerator.generate_bbox(question_number)
                        block["bbox"] = new_bbox
                        
                        all_blocks.append(block)
            
            # 按頁碼重新組織
            new_chunks = BBoxGenerator.organize_by_page(all_blocks)
            output["result"]["chunks"] = new_chunks
            
        except Exception as e:
            print(f"⚠️  bbox 標準化失敗：{e}")
        
        return output
    
    def _build_system_prompt(self, examples: list, policy: str) -> str:
        """構建系統提示詞"""
        with open("prompt_templates/system.txt", 'r', encoding='utf-8') as f:
            template = f.read()
        
        # 格式化範例
        examples_text = ""
        for i, ex in enumerate(examples, 1):
            examples_text += f"\n### 範例 {i}\n"
            examples_text += f"**輸入：**\n```json\n{json.dumps(ex['input'], ensure_ascii=False, indent=2)[:500]}...\n```\n"
            examples_text += f"**輸出：**\n```json\n{json.dumps(ex['output'], ensure_ascii=False, indent=2)[:500]}...\n```\n"
        
        return template.format(
            similar_examples=examples_text,
            policy=policy
        )
    
    def save_as_example(self, input_data: dict, output_data: dict, category: str):
        """
        將成功轉換的案例存為範例
        
        Args:
            input_data: 原始輸入
            output_data: 轉換結果
            category: 類別
        """
        examples_dir = Path(f"../knowledge/{category}/examples")
        examples_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成檔名（使用時間戳）
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        input_file = examples_dir / f"ex_{timestamp}_input.json"
        output_file = examples_dir / f"ex_{timestamp}_output.json"
        
        with open(input_file, 'w', encoding='utf-8') as f:
            json.dump(input_data, f, ensure_ascii=False, indent=2)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 已儲存為範例：{input_file.name}")


# CLI 使用
if __name__ == "__main__":
    import sys
    
    converter = ExamConverter()
    
    # 讀取輸入檔案
    input_file = sys.argv[1] if len(sys.argv) > 1 else "../knowledge/math_test/examples/ex1_input.json"
    
    with open(input_file, 'r', encoding='utf-8') as f:
        input_data = json.load(f)
    
    # 轉換
    output = converter.convert(input_data)
    
    # 輸出結果
    print("\n" + "="*50)
    print("轉換結果：")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    
    # 詢問是否儲存為範例
    save = input("\n是否儲存為範例？(y/n): ")
    if save.lower() == 'y':
        converter.save_as_example(input_data, output, output["meta"]["category"])
