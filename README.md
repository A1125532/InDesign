# PDF 考卷智慧轉檔（InDesign / 版面 JSON）

本專案將 **PDF 考卷**（含掃描稿）透過雲端解析、繁體化前處理，再經 **大型語言模型（LLM）與 RAG（檢索增強）** 轉成結構化的 **版面／考卷 JSON**，目標是銜接 **Adobe InDesign** 或後續自動排版流程。

專案分為兩個子目錄：

| 目錄 | 角色 |
|------|------|
| **`ingest/`** | 進件與前處理：Web 上傳、Reducto PDF 解析、繁體中文轉換、呼叫轉換後端 |
| **`convert/`** | 考卷結構轉換：規則分類、向量檢索範例、GPT 產生標準 JSON、輸出驗證與 bbox 處理 |

---

## 使用到的程式語言與技術

### 後端（主要）

- **Python 3**
- **`ingest/`**
  - **Flask**：HTTP API 與靜態頁
  - **Reducto**（`reducto` / `reductoai` SDK）：PDF 上傳與 `parse` 解析，輸出 JSON
  - **OpenCC**（`opencc-python-reimplemented`）：簡繁轉換（台灣繁體取向），並對 JSON 遞迴處理字串
  - **`subprocess`**：呼叫 `test_reducto.py` 與 `convert/server/app.py`
- **`convert/server/`**
  - **OpenAI API**（`openai`）：Chat Completions，強制 JSON 輸出
  - **Pydantic**：輸入／輸出結構驗證（`schema.py`）
  - **sentence-transformers**：多語句向量模型 `paraphrase-multilingual-MiniLM-L12-v2`，用於範例相似度檢索
  - **NumPy**、**scikit-learn**：向量運算與相似度（RAG 檢索）
  - **python-dotenv**：從 `.env` 讀取 `OPENAI_API_KEY` 等

### 前端（網頁 UI）

- **HTML**
- **JavaScript**（原生 `fetch`，無打包工具）
- **Tailwind CSS**（透過 CDN：`index.html` 內載入），含深色模式切換

### 測試

- **`pytest`**（`convert/server/requirements.txt` 列出；測試位於 `convert/tests/`）

---

## 目錄結構（精簡）

```
new/
├── README.md                 # 本說明
├── venv/                     # 可選：本機虛擬環境（勿提交敏感資料）
├── ingest/                   # 進件服務
│   ├── app.py                # Flask 主程式（上傳 → Reducto → 繁體 → convert）
│   ├── app_跑unknown.py      # 另一版流程（含複製至 examples 等步驟）
│   ├── test_reducto.py       # CLI：單檔 PDF → downloads/*.json
│   ├── templates/index.html  # 上傳與轉換 UI
│   ├── uploads/              # 上傳的 PDF
│   ├── downloads/            # 中間與最終 JSON（部分為執行產物）
│   └── requ.txt              # 手寫安裝備忘（pip 套件）
└── convert/                  # 轉換後端與知識庫
    ├── readme.txt            # 內部目錄樹說明
    ├── knowledge/            # 各類考卷：policy、presets、examples（RAG few-shot）
    └── server/
        ├── app.py            # ExamConverter：CLI 與轉換邏輯
        ├── rag.py            # 範例載入與向量檢索
        ├── rules.py          # 類別偵測等規則
        ├── schema.py         # Pydantic 模型
        ├── bbox_generator.py # 數學卷 bbox 標準化
        ├── prompt_templates/ # system / user 提示詞模板
        └── requirements.txt  # Python 依賴清單
```

---

## 系統資料流（概念）

1. 使用者於 **`ingest`** 網頁上傳 PDF → `POST /upload` 存至 `ingest/uploads/`。
2. 使用者觸發處理 → `POST /process`：
   - 執行 **`ingest/test_reducto.py`**（Reducto 解析 PDF）→ 寫入 `ingest/downloads/<檔名>.json`。
   - 將 JSON **繁體化** 後產生 `*_merged.json`。
   - 以子程序執行 **`convert/server/app.py`**，並可設定環境變數 **`CATEGORY_OVERRIDE=math_exam`**（主流程 `app.py` 目前固定數學卷）。
3. **`convert`** 讀取合併後的 JSON：偵測類別 → RAG 取相似範例與 policy → 呼叫 GPT → 驗證輸出 →（數學卷）bbox 調整 → 將 input/output 寫回 `convert/knowledge/<category>/examples/`。
4. **`ingest`** 將最終 `*_merged_output.json` 複製到 `ingest/downloads/`，前端以 **`GET /download/<檔名>`** 下載。

---

## 環境需求

- **Python 3.10+**（建議與本機已測試版本一致）
- **網路連線**：Reducto API、OpenAI API、首次執行時下載 **Sentence-Transformers** 模型
- **Windows / macOS / Linux** 皆可；下列指令以 **Windows PowerShell** 為例

---

## 安裝步驟

### 1. 建立虛擬環境（建議在專案根目錄）

```powershell
cd D:\UserHomeDir\Downloads\new
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. 安裝 `ingest` 依賴

`ingest/requ.txt` 建議的套件（可依實際 Reducto SDK 版本調整）：

```powershell
pip install flask reducto opencc-python-reimplemented
# 若專案固定使用特定 Reducto 客戶端版本，可再安裝：
pip install "reductoai==0.13.0"
```

### 3. 安裝 `convert/server` 依賴

```powershell
pip install -r convert\server\requirements.txt
```

> **注意**：`sentence-transformers` 會一併拉 **PyTorch** 等較大依賴，首次安裝時間較長。

### 4. 設定環境變數（`convert/server/.env`）

在 **`convert/server/`** 目錄建立 **`.env`**（此檔已列入根目錄 **`.gitignore`**，請勿把含金鑰的檔案提交到 GitHub）。請自行向服務商取得金鑰後填入，**不要**把真實金鑰寫進 README 或任何會公開的檔案。

必填變數名稱（值請在本機 `.env` 內自行填寫）：

```env
OPENAI_API_KEY=
REDUCTO_API_KEY=
```

可選：

```env
# 強制覆寫考卷類別（與 ingest 主流程傳入的 math_exam 一致）
CATEGORY_OVERRIDE=math_exam
```

### 5. Reducto 與 `ingest` 腳本

**`ingest/test_reducto.py`**、**`ingest/local.py`**、**`ingest/official.py`** 會透過 **`ingest/convert_env.py`** 讀取與 **`convert/server/.env`** 相同的 **`REDUCTO_API_KEY`**。執行前請確認已安裝 **`python-dotenv`**（見 **`ingest/requ.txt`**）。

---

## 執行步驟

### A. 一鍵 Web 流程（建議）

1. 啟用虛擬環境後：

   ```powershell
   cd D:\UserHomeDir\Downloads\new\ingest
   python app.py
   ```

2. 瀏覽器開啟 Flask 預設位址：**http://127.0.0.1:5000/**
3. 上傳 PDF → 在頁面輸入「轉換規則」文字後按送出（前端會呼叫 **`/process`**；後端實際管線為 Reducto + 繁體 + `convert`，與 UI 文案中的 INDD 產出為**產品願景**，目前主交付物為 **JSON**）。
4. 完成後依提示下載 **`ingest/downloads/`** 內對應的 **`*_merged_output.json`**。

### B. 僅測試 Reducto（單檔 PDF → JSON）

```powershell
cd D:\UserHomeDir\Downloads\new\ingest
python test_reducto.py "路徑\你的考卷.pdf"
```

輸出：`ingest/downloads/<檔名>.json`

### C. 僅執行考卷轉換（已有 OCR／Reducto JSON）

在 **`convert/server`** 目錄執行（確保 `.env` 或環境變數已設定）：

```powershell
cd D:\UserHomeDir\Downloads\new\convert\server
python app.py
# 或指定輸入檔：
python app.py "..\..\ingest\downloads\某份_merged.json"
```

未指定檔名時，預設讀取 `convert/knowledge/math_exam/examples/ex1_input.json`。

### D. 執行單元測試（`convert`）

```powershell
cd D:\UserHomeDir\Downloads\new\convert
pytest tests\ -v
```

### E. 替代 Flask 入口（`app_跑unknown.py`）

若需使用 **`ingest/app_跑unknown.py`** 的流程（含將 merged JSON 複製到 `convert/knowledge/.../examples` 等），啟動方式與 `app.py` 相同，但需將執行檔改為該檔名（並自行確認路由是否與目前 `templates` 一致）。

---

## HTTP API（`ingest/app.py`）

| 方法與路徑 | 說明 |
|------------|------|
| `GET /` | 回傳上傳／轉換頁（`templates/index.html`） |
| `POST /upload` | `multipart/form-data`，欄位名 **`file`**，上傳 PDF |
| `POST /process` | JSON body：`{"filename": "<已上傳檔名>", "rules": "..."}`（`rules` 目前後端未強制使用，但前端會傳） |
| `GET /download/<path:filename>` | 下載 `ingest/downloads/` 內檔案 |

---

## `convert` 知識庫與模型

- **`convert/knowledge/<category>/`**：`policy.md`（切段與標註規範）、`presets.json`、`styles_map.json`。
- **`examples/`**：成對的 `*_input.json` / `*_output.json`，供 RAG 檢索與 few-shot。
- **GPT 模型**：`convert/server/app.py` 內目前使用 **`gpt-4o-2024-11-20`**（若需更換，請改程式內 `model` 參數並自行評估成本與相容性）。
- **嵌入模型**：`rag.py` 使用 **`paraphrase-multilingual-MiniLM-L12-v2`**，首次執行會自動下載。

---

## 疑難排解

| 現象 | 可能原因 |
|------|----------|
| Reducto 失敗 | API 金鑰、網路、或 SDK 版本與官方 API 不相容 |
| OpenAI 錯誤 | `OPENAI_API_KEY` 未設定或額度／權限問題 |
| 找不到 `convert/server/app.py` | 請確認專案根目錄下 **`ingest` 與 `convert` 為同層目錄**（`ingest/app.py` 以 `../convert/server/app.py` 呼叫） |
| 編碼錯誤（Windows cp950） | `ingest` 已對子程序設定 `PYTHONUTF8`、`PYTHONIOENCODING`；若獨立執行 `convert`，建議終端機使用 UTF-8 |
| 首次 RAG 很慢 | 正在下載 Sentence-Transformers 權重，請保持網路暢通 |

---

## 授權與安全

- 本 README 不涵蓋授權條款；若專案日後開源請自行補上 `LICENSE`。
- **切勿**將 **OpenAI**、**Reducto** 金鑰與內含個資的考卷提交至公開儲存庫。建議將 **`convert/server/.env`**、**`ingest/uploads/`**、**大型 JSON 產物** 列入 `.gitignore`。

---

## 版本備註

- **`ingest/requ.txt`** 特別提到：若使用虛擬環境，**`reductoai==0.13.0`** 需在正確的解譯器環境安裝，避免呼叫到全域舊版套件。

若你希望 README 再補上「截圖流程」或「JSON 欄位說明」，可指定要對齊的輸出範例檔名後再擴充一節即可。
