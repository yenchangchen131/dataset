# 使用指南：繁體中文 RAG 評測資料集

本文件說明如何載入、使用本資料集 (`queries.json` 與 `corpus.json`) 來進行 RAG 系統的評測。

## 1. 資料載入

資料集為標準 JSON 格式，可使用 Python `json` 套件直接載入。

```python
import json

# 1. 載入評測題庫 (50 題)
with open("data/processed/queries.json", "r", encoding="utf-8") as f:
    queries = json.load(f)

# 2. 載入文檔庫 (500 篇)
with open("data/processed/corpus.json", "r", encoding="utf-8") as f:
    corpus = json.load(f)

# 建立檢索索引 (Doc ID -> Content)
corpus_map = {doc["doc_id"]: doc["content"] for doc in corpus}
```

## 2. 評測流程範例

一般的 RAG 評測流程如下：

1. **建立索引 (Indexing)**：將 `corpus` 中的 500 篇文章轉換為向量並存入向量資料庫 (Vector DB)。
   - **Embedding Model**: `text-embedding-3-small`
   - **Chunking Strategy**: 不進行切分 (No Chunking)，直接使用完整文章內容 (content)。
2. **檢索 (Retrieval)**：針對每個 `query`，檢索出 Top-5 篇相關文章。
   - 若涉及 LLM (如重排序、查詢擴展)，統一使用 `gpt-4o-mini`。
3. **生成 (Generation)**：將檢索到的文章作為 Context，輸入 LLM 產生這題的答案。
   - **Generation Model**: `gpt-4o-mini`
4. **評分 (Scoring)**：計算檢索命中率與答案準確度。

## 3. 計算評測指標

### 3.1 檢索指標：Recall Score (Recall@5)

針對每個問題，計算檢索出的 Top-5 文檔中，包含了幾篇該問題的標準答案 (`gold_doc_ids`)。
針對多跳問題，觀察是否找齊所有相關文檔。

```python
k = 5
total_recall = 0

for q in queries:
    # 您的系統檢索結果 (回傳 doc_ids)
    retrieved_ids = your_rag_system.retrieve(q["question"], top_k=k)
  
    # 計算找到幾篇 Gold Docs
    gold_ids = set(q["gold_doc_ids"])
    found_count = sum(1 for doc_id in retrieved_ids if doc_id in gold_ids)
  
    # 計算該題召回分數 (找到篇數 / 總篇數)
    score = found_count / len(gold_ids)
    total_recall += score
  
    print(f"Question: {q['question']}")
    print(f"Found {found_count}/{len(gold_ids)} gold docs.")

average_recall = total_recall / len(queries)
print(f"Average Recall@{k}: {average_recall:.2%}")
```

### 3.2 生成指標：LLM-as-a-Judge

由於翻譯後的答案可能有用詞差異，不使用字串完全比對 (Exact Match)。使用 LLM ( GPT-4o-mini) 來判斷語意正確性。

**Prompt 範例：**

> 請判斷「模型回答」是否與「標準答案」語意一致。
>
> 問題：{question}
> 標準答案：{gold_answer}
> 模型回答：{model_answer}
>
> 如果語意一致請回答 "Pass"，否則回答 "Fail"。

計算通過率。

## 4. 資料欄位說明

### Query (`queries.json`)

| 欄位              | 說明                                                 |
| ----------------- | ---------------------------------------------------- |
| `question_id`   | 唯一識別碼                                           |
| `question`      | 繁體中文問題                                         |
| `gold_answer`   | 標準答案 (供評測比對)                                |
| `gold_doc_ids`  | 正解文檔 ID 列表 (供檢索評測)                        |
| `question_type` | `single-hop` 或 `multi-hop` (可依此分類分析效能) |

### Corpus (`corpus.json`)

| 欄位                | 說明                                         |
| ------------------- | -------------------------------------------- |
| `doc_id`          | 唯一識別碼 (與 queries 對應)                 |
| `content`         | 文章內文                                     |
| `original_source` | 原始資料來源 (如 `squad`, `hotpotqa`...) |
| `is_gold`         | 標示該文檔是否為某個問題的正解 (True/False)  |
