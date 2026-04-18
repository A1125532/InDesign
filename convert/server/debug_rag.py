import sys
from pathlib import Path

# 加入路徑
sys.path.insert(0, str(Path(__file__).parent))

from rag import ExamRAG
import json

print("="*60)
print("🔍 RAG 系統除錯")
print("="*60)

# 初始化 RAG
rag = ExamRAG(knowledge_base="../knowledge")

# 1. 檢查路徑
examples_dir = rag.knowledge_base / "math_exam" / "examples"
print(f"\n1. 檢查路徑")
print(f"   知識庫路徑：{rag.knowledge_base.absolute()}")
print(f"   範例路徑：{examples_dir.absolute()}")
print(f"   路徑存在：{examples_dir.exists()}")

# 2. 列出所有檔案
if examples_dir.exists():
    all_files = list(examples_dir.iterdir())
    print(f"\n2. 資料夾內容（共 {len(all_files)} 個檔案）")
    for f in all_files:
        print(f"   - {f.name} ({f.stat().st_size} bytes)")
    
    # 3. 檢查配對
    input_files = list(examples_dir.glob("*_input.json"))
    print(f"\n3. 輸入檔案（共 {len(input_files)} 個）")
    for f in input_files:
        output_file = f.with_name(f.stem.replace("_input", "_output") + ".json")
        has_output = output_file.exists()
        print(f"   - {f.name} → {output_file.name} {'✓' if has_output else '✗'}")
        
        # 檢查 JSON 格式
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                print(f"      輸入 JSON 格式正確，keys: {list(data.keys())}")
        except Exception as e:
            print(f"      ⚠️  輸入 JSON 格式錯誤：{e}")
        
        if has_output:
            try:
                with open(output_file, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    print(f"      輸出 JSON 格式正確，keys: {list(data.keys())}")
            except Exception as e:
                print(f"      ⚠️  輸出 JSON 格式錯誤：{e}")
else:
    print(f"\n⚠️  路徑不存在！")

# 4. 測試載入
print(f"\n4. 測試 load_examples()")
try:
    examples = rag.load_examples("math_exam")
    print(f"   ✓ 成功載入 {len(examples)} 個範例")
    
    for i, ex in enumerate(examples, 1):
        print(f"\n   範例 {i}:")
        print(f"   - 檔名：{ex.get('filename', 'N/A')}")
        print(f"   - 輸入 keys：{list(ex.get('input', {}).keys())}")
        print(f"   - 輸出 keys：{list(ex.get('output', {}).keys())}")
        
        # 檢查內容提取
        try:
            content = ex["input"]["result"]["chunks"][0]["content"]
            print(f"   - 內容長度：{len(content)} 字元")
            print(f"   - 內容預覽：{content[:100]}...")
        except Exception as e:
            print(f"   - ⚠️  無法提取內容：{e}")
    
except Exception as e:
    print(f"   ✗ 載入失敗：{e}")
    import traceback
    traceback.print_exc()

# 5. 測試檢索
print(f"\n5. 測試 retrieve_similar()")
try:
    query = "設 x 為正數，求最大值"
    results = rag.retrieve_similar(query, "math_exam", top_k=2)
    print(f"   ✓ 檢索到 {len(results)} 個結果")
    
    for i, r in enumerate(results, 1):
        print(f"\n   結果 {i}:")
        print(f"   - 檔名：{r.get('filename', 'N/A')}")
        print(f"   - 相似度：{r.get('similarity', 0):.4f}")
        
except Exception as e:
    print(f"   ✗ 檢索失敗：{e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
