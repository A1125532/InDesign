from sentence_transformers import SentenceTransformer
import numpy as np

print("載入 Embedding 模型...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("✓ 模型載入成功")

# 測試文字
text1 = "設 x 為正數，求最大值"
text2 = "1. 設 x為正數,請問下列哪一個選項的數值最大?"

# 編碼
emb1 = model.encode([text1])
emb2 = model.encode([text2])

# 計算相似度
from sklearn.metrics.pairwise import cosine_similarity
similarity = cosine_similarity(emb1, emb2)[0][0]

print(f"\n文字 1：{text1}")
print(f"文字 2：{text2}")
print(f"相似度：{similarity:.4f}")

if similarity > 0.3:
    print("✓ 相似度正常")
else:
    print("⚠️  相似度過低")
