"""
修復問題腳本
將未翻譯的英文陳述句，根據其答案與黃金文檔，改寫為繁體中文問句。
"""

import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 載入環境變數
load_dotenv()

# 初始化 OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 路徑設定
BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

MODEL = "gpt-4o-mini"

# 設定標準輸出編碼為 utf-8 (避免 Windows console error)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def load_json(filepath: Path) -> list[dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data: list[dict], filepath: Path) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_question(statement: str, answer: str, context: str) -> str:
    """使用 GPT-4o-mini 生成中文問句"""
    
    prompt = f"""
你是一個專業的資料集編輯。
以下是一個「英文陳述句」，它原本應該是一個問題，但被寫成了陳述句。
請根據這個陳述句、標準答案以及參考文檔，將其改寫成一個流暢的「台灣繁體中文問句」。

要求：
1. 問句必須能透過參考文檔推導出標準答案。
2. 問句的語意應對應原始的英文陳述句。
3. 只回傳問句本身，不要有其他說明。

[原始英文陳述]
{statement}

[標準答案]
{answer}

[參考文檔]
{context}

[繁體中文問句]
"""
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "你是一個精確的問句改寫助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error producing question: {e}")
        return statement # 發生錯誤則回傳原句

def main():
    print("=" * 60)
    print("開始修復未翻譯問題")
    print("=" * 60)
    
    queries_path = PROCESSED_DIR / "queries.json"
    corpus_path = PROCESSED_DIR / "corpus.json"
    
    queries = load_json(queries_path)
    corpus = load_json(corpus_path)
    
    # 建立 doc_id -> content 索引以便快速查詢
    doc_map = {doc["doc_id"]: doc["content"] for doc in corpus}
    
    # 找出包含非中文字元且非 DRCD 來源的問題
    fixed_count = 0
    
    for q in queries:
        if q.get("source_dataset") == "drcd":
            continue
            
        question_text = q.get("question", "")
        if not any('\u4e00' <= c <= '\u9fff' for c in question_text):
            print(f"\n[處理中] ID: {q.get('question_id')}")
            print(f"  原始: {question_text}")
            
            # 取得相關資訊
            gold_answer = q.get("gold_answer", "")
            gold_doc_ids = q.get("gold_doc_ids", [])
            
            # 串接黃金文檔內容 (取前兩篇避免過長，通常 2hop 就夠了)
            context_texts = []
            for doc_id in gold_doc_ids[:2]:
                if doc_id in doc_map:
                    context_texts.append(doc_map[doc_id])
            
            full_context = "\n---\n".join(context_texts)
            
            # 生成新問句
            new_question = generate_question(question_text, gold_answer, full_context)
            
            print(f"  修正: {new_question}")
            q["question"] = new_question
            fixed_count += 1
            
    if fixed_count > 0:
        print(f"\n共修復了 {fixed_count} 個問題。")
        save_json(queries, queries_path)
        print(f"已更新 {queries_path}")
    else:
        print("\n沒有發現需要修復的問題。")

if __name__ == "__main__":
    main()
