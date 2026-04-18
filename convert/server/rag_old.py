import json
import os
from pathlib import Path
from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer

class ExamRAG:
    """考卷範例檢索系統"""
    
    def __init__(self, knowledge_base: str = "../knowledge"):
        self.knowledge_base = Path(knowledge_base)
        self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        self.examples_cache = {}
        self.embeddings_cache = {}
        
    def load_examples(self, category: str) -> List[Dict]:
        """
        載入特定類別的範例
        
        Args:
            category: 如 'math_exam'
            
        Returns:
            [{"input": {...}, "output": {...}, "filename": "ex1"}, ...]
        """
        if category in self.examples_cache:
            return self.examples_cache[category]
        
        examples_dir = self.knowledge_base / category / "examples"
        examples = []
        
        if not examples_dir.exists():
            print(f"⚠️  範例目錄不存在：{examples_dir}")
            return []
        
        # 配對 input/output 檔案
        input_files = sorted(examples_dir.glob("*_input.json"))
        
        for input_file in input_files:
            output_file = input_file.with_name(input_file.stem.replace("_input", "_output") + ".json")
            
            if output_file.exists():
                try:
                    with open(input_file, 'r', encoding='utf-8') as f:
                        input_data = json.load(f)
                    with open(output_file, 'r', encoding='utf-8') as f:
                        output_data = json.load(f)
                    
                    examples.append({
                        "input": input_data,
                        "output": output_data,
                        "filename": input_file.stem
                    })
                except Exception as e:
                    print(f"⚠️  載入範例失敗 {input_file.name}: {e}")
        
        self.examples_cache[category] = examples
        print(f"✓ 載入 {len(examples)} 個 {category} 範例")
        return examples
    
    def retrieve_similar(self, query_text: str, category: str, top_k: int = 2) -> List[Dict]:
        """
        檢索最相似的範例
        
        Args:
            query_text: 當前考卷的 OCR 文字
            category: 考卷類別
            top_k: 返回前 k 個最相似範例
            
        Returns:
            相似範例列表，包含 input, output, similarity
        """
        examples = self.load_examples(category)
        
        if not examples:
            return []
        
        # 🔧 編碼查詢（取前 1000 字）
        query_embedding = self.model.encode([query_text[:1000]])
        
        # 🔧 編碼所有範例（使用快取）
        if category not in self.embeddings_cache:
            example_texts = [
                self._extract_text(ex["input"])[:1000]
                for ex in examples
            ]
            self.embeddings_cache[category] = self.model.encode(example_texts)
        
        example_embeddings = self.embeddings_cache[category]
        
        # 🔧 使用 cosine_similarity 計算相似度
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity(query_embedding, example_embeddings)[0]
        except Exception:
            # 後備方案：以 numpy 計算 cosine 相似度
            q = query_embedding[0]
            norms = np.linalg.norm(example_embeddings, axis=1) * (np.linalg.norm(q) + 1e-12)
            similarities = (example_embeddings @ q) / (norms + 1e-12)
        
        # 取前 k 個最相似的
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = []
        for i in top_indices:
            results.append({
                "input": examples[i]["input"],
                "output": examples[i]["output"],
                "filename": examples[i].get("filename", ""),
                "similarity": float(similarities[i])
            })
        
        return results

    def _extract_text(self, input_json: Dict) -> str:
        """由輸入 JSON 取出可檢索文本，盡量穩健處理結構差異。"""
        try:
            result = input_json.get("result", {})
            chunks = result.get("chunks", [])
            if not chunks:
                return ""
            # 取第一段內容
            content = chunks[0].get("content", "")
            return content if isinstance(content, str) else ""
        except Exception:
            return ""
    
    def load_policy(self, category: str) -> str:
        """載入轉換政策文件"""
        policy_file = self.knowledge_base / category / "policy.md"
        
        if policy_file.exists():
            with open(policy_file, 'r', encoding='utf-8') as f:
                return f.read()
        
        return ""
    
    def load_presets(self, category: str) -> Dict:
        """載入預設規則"""
        presets_file = self.knowledge_base / category / "presets.json"
        
        if presets_file.exists():
            with open(presets_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {}
