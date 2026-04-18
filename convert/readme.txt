convert/
  knowledge/
    math_exam/
      policy.md          # 切段與標註規範
      presets.json       # 版型設定（單欄/雙欄）
      styles_map.json    # 樣式鍵 → InDesign Paragraph Style 名稱
      examples/
        ex1_input.json   # OCR block 範例
        ex1_output.json  # 對應 layout 片段（Few-shot）
        ex2_input.json
        ex2_output.json
  server/
    app.py               # FastAPI 服務（RAG + LLM）
    rag.py               # 向量檢索封裝
    rules.py             # 題號/選項/公式 小規則（可選）
    schema.py            # Pydantic/JSON Schema 驗證
    prompt_templates/
      system.txt
      user_template.json
  storage/
    vectordb/            # FAISS/Chroma 資料
    cache/               # 回應快取
  tests/
    sample_ocr.json      # 你剛剛那頁 Reducto 結果