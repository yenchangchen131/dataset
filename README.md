# 繁體中文 RAG 效能評測微型資料集 (Micro-Scale TC-RAG Benchmark)

這是一個輕量級、針對繁體中文 RAG (Retrieval-Augmented Generation) 系統設計的評測資料集。透過從學術界標準資料集 (DRCD, SQuAD, HotpotQA, 2WikiMultiHopQA) 進行採樣與高品質翻譯，建立一個包含 **50 題問答 (Queries)** 與 **500 篇文檔 (Corpus)** 的測試基準。

## 🎯 專案目標

- **輕量化**：僅 50 題，可快速驗證系統效能。
- **在地化**：全數資料皆為台灣繁體中文 (Traditional Chinese, Taiwan)。
- **高鑑別度**：包含單跳 (Single-hop) 與多跳 (Multi-hop) 推理題型，並混入與正解高度相似的干擾文檔 (Hard Negatives)。

## 📊 資料集統計

| 來源資料集 | 題型 | 數量 | 說明 |
|------------|------|------|------|
| **DRCD** | 單跳 | 15 | 原生繁體中文資料 |
| **SQuAD** | 單跳 | 15 | 英文翻譯為繁中 |
| **HotpotQA** | 多跳 | 10 | 英文翻譯為繁中 (含干擾項) |
| **2Wiki** | 多跳 | 10 | 英文翻譯為繁中 (含干擾項) |
| **總計** | - | **50** | |

- **文檔庫 (Corpus)**: 總計 **500 篇**
  - **Gold Contexts**: ~70 篇 (正解)
  - **Negatives**: ~430 篇 (包含 Hard/Random Negatives)

## 🛠️ 安裝與環境設定

本專案使用 `uv` 進行套件管理。

1. **安裝相依套件**
   ```bash
   uv sync
   ```
   或手動安裝：
   ```bash
   uv add openai python-dotenv tqdm
   ```

2. **設定環境變數**
   請在專案根目錄建立 `.env` 檔案，並填入 OpenAI API Key (用於翻譯與修復)：
   ```ini
   OPENAI_API_KEY=sk-your-api-key-here
   ```

## 🚀 使用指南 (Pipeline)

請依序執行以下腳本以產生資料集：

### 0. 資料下載
下載原始資料集 (DRCD, SQuAD, HotpotQA, 2WikiMultiHopQA) 至 `data/raw/` 目錄。
```bash
uv run src/data_download.py
```

### 1. 資料提取與採樣
從 `data/raw/` 讀取原始資料，依照設定比例採樣，並組裝文檔池。
```bash
uv run src/process_data.py
```
> 產出：`data/processed/queries_raw.json`, `data/processed/corpus_raw.json`

### 2. 並行翻譯 (英翻中)
使用 GPT-4o-mini 多執行緒將英文資料翻譯為繁體中文。
```bash
uv run src/translate_data.py
```
> 產出：`data/processed/queries.json`, `data/processed/corpus.json`

### 3. 問題修復
針對翻譯過程中可能殘留的英文陳述句，透過語意改寫修正為中文問句。
```bash
uv run src/fix_questions.py
```

### 4. 資料驗證
檢查資料完整性、數量、Schema 與語言一致性。
```bash
uv run src/verify_data.py
```

## 📂 檔案結構

```
.
├── data/
│   ├── raw/               # 原始下載的資料集
│   └── processed/         # 產出的最終資料集
│       ├── queries.json   # 評測題庫 (50題)
│       └── corpus.json    # 文檔庫 (500篇)
├── src/
│   ├── data_download.py   # [Step 0] 原始資料下載
│   ├── process_data.py    # [Step 1] 採樣與提取
│   ├── translate_data.py  # [Step 2] 翻譯
│   ├── fix_questions.py   # [Step 3] 問題修復
│   ├── verify_data.py     # [Step 4] 驗證
│   └── inspect_suspicious.py # (工具) 檢視異常資料
├── docs/
│   └── Spec.md            # 詳細規格書
├── .env                   # API Key 設定檔
└── README.md              # 本文件
```

## 📝 輸出格式

### Query (`queries.json`)
```json
{
  "question_id": "uuid...",
  "question": "繁體中文問題...",
  "gold_answer": "標準答案",
  "gold_doc_ids": ["doc_uuid_1", "doc_uuid_2"],
  "source_dataset": "hotpotqa",
  "question_type": "multi-hop"
}
```

### Corpus (`corpus.json`)
```json
{
  "doc_id": "doc_uuid...",
  "content": "繁體中文文章內容...",
  "original_source": "hotpotqa",
  "original_id": "origin_id...", 
  "is_gold": true
}
```
