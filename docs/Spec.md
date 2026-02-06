
# 專案規格書：繁體中文 RAG 效能評測微型資料集 (Micro-Scale TC-RAG Benchmark)

**日期：** 2026-02-06

**語言：** 繁體中文 (Traditional Chinese)

---

## 1. 專案概述 (Project Overview)

本計畫旨在建立一個 **輕量級 (Lightweight)** 、**低成本 (Cost-Effective)** 且**在地化 (Localized)** 的 RAG 評測資料集。

透過將學術界標準的檢索問答資料集轉換為繁體中文，並採用 **500 篇規模的混合文檔池 (Global Pool)** 策略，快速驗證 RAG 系統在單跳、多跳推理及高雜訊環境下的檢索與生成效能。

---

## 2. 資料採樣策略 (Data Sampling Strategy)

目標總題數為  **50 題** ，依據難度與推理類型進行配比：

| **資料集來源**      | **原始類型** | **採樣數量** | **測試重點與理由**                                                                    |
| ------------------------- | ------------------ | ------------------ | ------------------------------------------------------------------------------------------- |
| **DRCD**            | 繁中/單跳          | **15 題**    | **(原生基準)**作為 Baseline，無翻譯誤差，測試模型對原生繁體中文的檢索理解能力。             |
| **SQuAD**           | 英文/單跳          | **15 題**    | **(基礎能力)**經典閱讀理解任務，評估基礎的事實檢索與問答能力。                              |
| **HotpotQA**        | 英文/多跳          | **10 題**    | **(高難度)**測試「跨文檔推理」能力。特點是包含大量與正解高度相似的干擾項 (Hard Negatives)。 |
| **2WikiMultiHopQA** | 英文/多跳          | **10 題**    | **(實體關聯)**測試模型在多個實體 (Entity) 間建立邏輯關聯的能力。                            |
| **總計**            | -                  | **50 題**    | 單跳 30 題 (60%) / 多跳 20 題 (40%)                                                         |

---

## 3. 文檔池架構 (Corpus Architecture)

採用 **Global Pool (混合文檔池)** 模式，模擬真實知識庫環境。所有 Query 共享同一個檢索庫，總文檔數設定為  **500 篇** 。

### 3.1 組成成分 (Composition)

| **類別**                       | **預估數量**    | **來源與說明**                                                                                                                     |
| ------------------------------------ | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Gold Contexts (正解)**    | ~60-70 篇             | **(必要)**50 題 QA 對應的所有正確文檔。``*註：多跳問題通常對應 2 篇以上的文檔。*                                                |
| **2. Hard Negatives (困難)**   | ~40-50 篇             | **(必要)**來自 HotpotQA/2Wiki 的官方干擾項。``這些文檔與問題有高度關鍵字重疊，用於測試抗干擾能力。                                |
| **3. Random Negatives (隨機)** | **~380-400 篇** | **(雜訊填充)**從 SQuAD、Wikipedia 或其他來源隨機抽取。``大幅增加背景雜訊 (Needle-in-a-Haystack)，確保檢索器具備真實的語意區辨力。 |
| **總計**                       | **500 篇**      | 所有文檔混合並建立統一索引 (Index)。                                                                                                     |

### 3.2 語言處理標準

* **翻譯目標** ：台灣繁體中文 (Traditional Chinese, Taiwan)。
* **工具建議** ：具備長文本理解能力的 LLM (如 GPT-4o-mini)。
* **一致性要求** ：
* **專有名詞 (Entity Consistency)** ：Question 與 Document 中的人名、地名翻譯必須嚴格一致，避免因翻譯差異導致檢索失敗 (Mismatch)。
* **UUID 關聯** ：翻譯過程中，必須保留或生成 UUID 來連結 Question 與 Document，嚴禁依賴「標題字串比對」。

---

## 4. 資料結構定義 (Data Schema)

為確保通用性與程式讀取便利，產出資料需符合以下 JSON 格式。

### 4.1 文檔庫 (`corpus.json`)

**JSON**

```
[
  {
    "doc_id": "uuid-string-001",
    "content": "翻譯後的繁體中文文章內容...",
    "original_source": "hotpotqa",
    "original_id": "原始資料集中的ID (備查用)",
    "is_gold": true  // (Optional) 標記此文檔是否為某個問題的正解，方便分析
  },
  ...
]
```

### 4.2 評測題庫 (`queries.json`)

**JSON**

```
[
  {
    "question_id": "uuid-string-q01",
    "question": "翻譯後的繁體中文問題？",
    "gold_answer": "翻譯後的標準答案",
    "gold_doc_ids": [
      "uuid-string-001", 
      "uuid-string-005"
    ],
    "source_dataset": "hotpotqa",
    "question_type": "multi-hop" // 或 "single-hop"
  },
  ...
]
```

---

## 5. 處理流程 (Processing Pipeline)

1. **Extract (萃取)** ：

* 讀取本地 Parquet/JSON 資料集。
* 依照採樣策略 (15/15/10/10) 隨機抽取題目。
* 提取對應的 Gold Contexts 與 Hard Negatives。
* 補足 Random Negatives 直到總數達 500 篇。

1. **Transform (轉換/翻譯)** ：

* **批次翻譯** ：將 Question、Answer、Contexts 送入 LLM 進行翻譯。
* **ID 生成** ：為每一篇 Context 和 Question 生成新的 UUID。
* **格式化** ：整理為上述 JSON Schema。

1. **Load (載入)** ：

* 輸出最終的 `corpus.json` 與 `queries.json` 至 `dataset/data/processed/` 目錄。

---

## 6. 評估指標 (Evaluation Metrics)

### 6.1 檢索階段 (Retrieval)

* **Hit Rate (Recall@K)** ：
* 設定 `K = 5`。
* **判定標準** ：`gold_doc_ids` 中的 ID 是否出現在檢索結果的前 K 名中。
* 針對多跳問題，建議採用 **嚴格模式 (Strict)** ：必須找齊所有相關文檔才算得分()。

### 6.2 生成階段 (Generation)

* **LLM-as-a-Judge** ：
* 放棄傳統的 Exact Match (EM) 或 F1 Score (因為翻譯會導致用詞改變)。
* **方法** ：將「模型回答」與「標準答案」丟給 LLM，透過 Prompt 判斷語意一致性。
* **評分** ：Pass (通過) / Fail (失敗)。

---

## 7. 技術堆疊 (Tech Stack)

* **語言** ：Python 3.10+
* **套件管理** ：`uv` (推薦) 或 `pip`
* **核心函式庫** ：
* `datasets`: Hugging Face 資料集處理。
* `pandas`: 資料清洗與結構化。
* `openai` / `google-generativeai`: 用於翻譯與評測。
* `tqdm`: 進度顯示。
* `uuid`: 唯一識別碼生成。
