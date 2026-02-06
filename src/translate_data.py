"""
翻譯處理腳本 (多執行緒並行版)
使用 GPT-4o-mini 將英文資料翻譯成繁體中文。

輸入：
- data/processed/queries_raw.json
- data/processed/corpus_raw.json

輸出：
- data/processed/queries.json
- data/processed/corpus.json
"""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

# 載入環境變數
load_dotenv()

# 初始化 OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 路徑設定
BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# 翻譯設定
MODEL = "gpt-4o-mini"
MAX_WORKERS = 20  # 並行執行緒數
MAX_RETRIES = 3   # 最大重試次數


def load_json(filepath: Path) -> list[dict]:
    """載入 JSON 檔案"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: list[dict], filepath: Path) -> None:
    """儲存 JSON 檔案"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def translate_text(text: str, context_type: str = "general") -> str:
    """
    使用 GPT-4o-mini 翻譯單一文本
    """
    if not text or not text.strip():
        return text
    
    system_prompt = """你是一位專業的英翻繁體中文翻譯專家。請將以下英文文本翻譯成流暢、自然的台灣繁體中文。

翻譯要求：
1. 保持原文的語意和語氣(如果是問句就保持問句、直述句就保持直述句)，不要自行修正原文的語詞、句型。
2. 人名、地名等專有名詞使用台灣常見的翻譯方式，然後用括號標註原文
3. 數字、日期格式保持原樣
4. 如果原文已經是中文，直接返回原文
5. 只返回翻譯結果，不要添加任何解釋或說明
6. 嚴格禁止回答問題，僅進行翻譯"""

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.3,
                max_tokens=4096,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                sleep_time = 2 ** attempt  # 指數退避
                time.sleep(sleep_time)
            else:
                print(f"  [Error] 翻譯失敗: {str(e)[:100]}...")
                return text


def process_item(item: dict, fields: list[str]) -> dict:
    """
    處理單一項目的翻譯
    """
    # 複製避免修改原始物件
    translated_item = item.copy()
    
    # Check if needs translation
    source = translated_item.get("source_dataset") or translated_item.get("original_source", "")
    if source == "drcd":
        return translated_item
        
    # Translate fields
    for field in fields:
        if field in translated_item and translated_item[field]:
            translated_item[field] = translate_text(translated_item[field], field)
            
    return translated_item


def translate_batch_parallel(items: list[dict], fields: list[str], desc: str) -> list[dict]:
    """
    多執行緒並行翻譯
    """
    results = [None] * len(items)
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_index = {
            executor.submit(process_item, item, fields): i 
            for i, item in enumerate(items)
        }
        
        # Process as they complete
        for future in tqdm(as_completed(future_to_index), total=len(items), desc=desc):
            index = future_to_index[future]
            try:
                results[index] = future.result()
            except Exception as e:
                print(f"Item {index} generated an exception: {e}")
                results[index] = items[index]  # Fallback to original
                
    return results


def main():
    print("=" * 60)
    print(f"開始翻譯處理 (並行數: {MAX_WORKERS})")
    print("=" * 60)
    
    if not os.getenv("OPENAI_API_KEY"):
        print("錯誤：未找到 OPENAI_API_KEY")
        return
    
    print("\n[載入中間檔案]")
    queries_raw = load_json(PROCESSED_DIR / "queries_raw.json")
    corpus_raw = load_json(PROCESSED_DIR / "corpus_raw.json")
    
    print(f"  - 問答數量: {len(queries_raw)}")
    print(f"  - 文檔數量: {len(corpus_raw)}")
    
    # 翻譯問答
    print("\n[翻譯問答資料]")
    translated_queries = translate_batch_parallel(
        queries_raw, 
        ["question", "gold_answer"], 
        "翻譯問答"
    )
    
    # 翻譯文檔
    print("\n[翻譯文檔資料]")
    translated_corpus = translate_batch_parallel(
        corpus_raw, 
        ["content"], 
        "翻譯文檔"
    )
    
    # 儲存輸出
    print("\n[儲存輸出]")
    save_json(translated_queries, PROCESSED_DIR / "queries.json")
    save_json(translated_corpus, PROCESSED_DIR / "corpus.json")
    
    print(f"  - 已儲存: {PROCESSED_DIR / 'queries.json'}")
    print(f"  - 已儲存: {PROCESSED_DIR / 'corpus.json'}")
    print("\n完成！")


if __name__ == "__main__":
    main()
