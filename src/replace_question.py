"""
問題抽換腳本
將指定的問題抽換為同資料集的另一題，並同步更新 queries.json 與 corpus.json。

使用方式:
    uv run src/replace_question.py <question_id>
    
範例:
    uv run src/replace_question.py e7124c20-75c2-5d99-9acf-d2cba40228fa
"""

import json
import uuid
import random
import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 載入環境變數
load_dotenv()

# 初始化 OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 路徑設定
BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

MODEL = "gpt-4o-mini"

# 設定標準輸出編碼為 utf-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


def load_json(filepath: Path) -> list[dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: list[dict], filepath: Path) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def generate_doc_id(source: str, original_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{source}:{original_id}"))


def generate_question_id(source: str, original_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"q:{source}:{original_id}"))


TRANSLATION_PROMPT = """你是一位專業的英翻繁體中文翻譯專家。請將以下英文文本翻譯成流暢、自然的台灣繁體中文。

翻譯要求：
1. 保持原文的語意和語氣(如果是問句就保持問句、直述句就保持直述句)，不要自行修正原文的語詞、句型。
2. 人名、地名等專有名詞使用台灣常見的翻譯方式，然後用括號標註原文
3. 數字、日期格式保持原樣
4. 如果原文已經是中文，直接返回原文
5. 只返回翻譯結果，不要添加任何解釋或說明
6. 嚴格禁止回答問題，僅進行翻譯"""


def translate_text(text: str) -> str:
    """使用 GPT-4o-mini 翻譯英文為繁體中文"""
    if not text or any('\u4e00' <= c <= '\u9fff' for c in text):
        return text  # 已經是中文或空字串
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": TRANSLATION_PROMPT},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"翻譯錯誤: {e}")
        return text


def get_used_contexts(queries: list[dict], corpus: list[dict]) -> set[str]:
    """取得目前已使用的所有 context"""
    return {doc["content"] for doc in corpus}


def get_used_question_ids(queries: list[dict]) -> set[str]:
    """取得目前已使用的所有 question_id，避免重複"""
    return {q["question_id"] for q in queries}


def extract_drcd_candidate(data: list[dict], used_contexts: set[str], used_question_ids: set[str]) -> dict | None:
    """從 DRCD 中提取一個新的 QA"""
    candidates = []
    for article in data:
        for para in article.get("paragraphs", []):
            context = para.get("context", "")
            if not context or context in used_contexts:
                continue
            for qa in para.get("qas", []):
                original_id = qa.get("id", str(uuid.uuid4()))
                question_id = generate_question_id("drcd", original_id)
                # 跳過已存在的問題
                if question_id in used_question_ids:
                    continue
                candidates.append({
                    "qa": qa,
                    "context": context,
                    "title": article.get("title", ""),
                })
    
    if not candidates:
        return None
    
    selected = random.choice(candidates)
    qa = selected["qa"]
    original_id = qa.get("id", str(uuid.uuid4()))
    doc_id = generate_doc_id("drcd", original_id)
    question_id = generate_question_id("drcd", original_id)
    
    answers = qa.get("answers", [])
    answer_text = answers[0].get("text", "") if answers else ""
    
    return {
        "query": {
            "question_id": question_id,
            "question": qa.get("question", ""),
            "gold_answer": answer_text,
            "gold_doc_ids": [doc_id],
            "source_dataset": "drcd",
            "question_type": "single-hop",
        },
        "query_raw": {
            "question_id": question_id,
            "question": qa.get("question", ""),
            "gold_answer": answer_text,
            "gold_doc_ids": [doc_id],
            "source_dataset": "drcd",
            "question_type": "single-hop",
        },
        "docs": [{
            "doc_id": doc_id,
            "content": selected["context"],
            "original_source": "drcd",
            "original_id": original_id,
            "is_gold": True,
        }],
        "docs_raw": [{
            "doc_id": doc_id,
            "content": selected["context"],
            "original_source": "drcd",
            "original_id": original_id,
            "is_gold": True,
        }],
    }


def extract_squad_candidate(data: list[dict], used_contexts: set[str], used_question_ids: set[str]) -> dict | None:
    """從 SQuAD 中提取一個新的 QA"""
    # 過濾掉已使用的 context 和 question_id
    candidates = []
    for item in data:
        if item.get("context", "") in used_contexts:
            continue
        original_id = item.get("id", str(uuid.uuid4()))
        question_id = generate_question_id("squad", original_id)
        if question_id in used_question_ids:
            continue
        candidates.append(item)
    
    if not candidates:
        return None
    
    selected = random.choice(candidates)
    original_id = selected.get("id", str(uuid.uuid4()))
    doc_id = generate_doc_id("squad", original_id)
    question_id = generate_question_id("squad", original_id)
    
    answers = selected.get("answers", {})
    answer_texts = answers.get("text", [])
    answer_text = answer_texts[0] if answer_texts else ""
    
    # 翻譯
    print("  翻譯問題...")
    translated_question = translate_text(selected.get("question", ""))
    print("  翻譯答案...")
    translated_answer = translate_text(answer_text)
    print("  翻譯文檔...")
    translated_content = translate_text(selected.get("context", ""))
    
    return {
        "query": {
            "question_id": question_id,
            "question": translated_question,
            "gold_answer": translated_answer,
            "gold_doc_ids": [doc_id],
            "source_dataset": "squad",
            "question_type": "single-hop",
        },
        "query_raw": {
            "question_id": question_id,
            "question": selected.get("question", ""),
            "gold_answer": answer_text,
            "gold_doc_ids": [doc_id],
            "source_dataset": "squad",
            "question_type": "single-hop",
        },
        "docs": [{
            "doc_id": doc_id,
            "content": translated_content,
            "original_source": "squad",
            "original_id": original_id,
            "is_gold": True,
        }],
        "docs_raw": [{
            "doc_id": doc_id,
            "content": selected.get("context", ""),
            "original_source": "squad",
            "original_id": original_id,
            "is_gold": True,
        }],
    }


def extract_hotpotqa_candidate(data: list[dict], used_contexts: set[str], used_question_ids: set[str]) -> dict | None:
    """從 HotpotQA 中提取一個新的 QA (含 hard negatives)"""
    random.shuffle(data)
    
    for item in data:
        original_id = item.get("id", str(uuid.uuid4()))
        question_id = generate_question_id("hotpotqa", original_id)
        
        # 跳過已存在的問題
        if question_id in used_question_ids:
            continue
        
        context_data = item.get("context", {})
        titles = context_data.get("title", [])
        sentences_list = context_data.get("sentences", [])
        
        supporting_facts = item.get("supporting_facts", {})
        gold_titles = set(supporting_facts.get("title", []))
        
        # 檢查是否有未使用的 context
        all_contents = []
        for i, title in enumerate(titles):
            if i >= len(sentences_list):
                continue
            sentences = sentences_list[i]
            content = " ".join(sentences) if isinstance(sentences, list) else str(sentences)
            if content.strip():
                all_contents.append(content)
        
        if any(c in used_contexts for c in all_contents):
            continue
        
        # 提取文檔
        docs = []
        docs_raw = []
        gold_doc_ids = []
        
        for i, title in enumerate(titles):
            if i >= len(sentences_list):
                continue
            
            sentences = sentences_list[i]
            content = " ".join(sentences) if isinstance(sentences, list) else str(sentences)
            
            if not content.strip():
                continue
            
            doc_original_id = f"{original_id}_{title}"
            doc_id = generate_doc_id("hotpotqa", doc_original_id)
            
            print(f"  翻譯文檔: {title}...")
            translated_content = translate_text(content)
            
            is_gold = title in gold_titles
            docs.append({
                "doc_id": doc_id,
                "content": translated_content,
                "original_source": "hotpotqa",
                "original_id": doc_original_id,
                "is_gold": is_gold,
            })
            docs_raw.append({
                "doc_id": doc_id,
                "content": content,
                "original_source": "hotpotqa",
                "original_id": doc_original_id,
                "is_gold": is_gold,
            })
            
            if is_gold:
                gold_doc_ids.append(doc_id)
        
        if not gold_doc_ids:
            continue
        
        # 翻譯問題與答案
        print("  翻譯問題...")
        translated_question = translate_text(item.get("question", ""))
        print("  翻譯答案...")
        translated_answer = translate_text(item.get("answer", ""))
        
        return {
            "query": {
                "question_id": question_id,
                "question": translated_question,
                "gold_answer": translated_answer,
                "gold_doc_ids": gold_doc_ids,
                "source_dataset": "hotpotqa",
                "question_type": "multi-hop",
            },
            "query_raw": {
                "question_id": question_id,
                "question": item.get("question", ""),
                "gold_answer": item.get("answer", ""),
                "gold_doc_ids": gold_doc_ids,
                "source_dataset": "hotpotqa",
                "question_type": "multi-hop",
            },
            "docs": docs,
            "docs_raw": docs_raw,
        }
    
    return None


def extract_2wiki_candidate(data: list[dict], used_contexts: set[str], used_question_ids: set[str]) -> dict | None:
    """從 2WikiMultiHopQA 中提取一個新的 QA (含 hard negatives)"""
    random.shuffle(data)
    
    for item in data:
        original_id = item.get("id", str(uuid.uuid4()))
        question_id = generate_question_id("2wiki", original_id)
        
        # 跳過已存在的問題
        if question_id in used_question_ids:
            continue
        
        context_data = item.get("context", {})
        titles = context_data.get("title", [])
        sentences_list = context_data.get("sentences", [])
        
        supporting_facts = item.get("supporting_facts", {})
        gold_titles = set(supporting_facts.get("title", []))
        
        # 檢查是否有未使用的 context
        all_contents = []
        for i, title in enumerate(titles):
            if i >= len(sentences_list):
                continue
            sentences = sentences_list[i]
            content = " ".join(sentences) if isinstance(sentences, list) else str(sentences)
            if content.strip():
                all_contents.append(content)
        
        if any(c in used_contexts for c in all_contents):
            continue
        
        # 提取文檔
        docs = []
        docs_raw = []
        gold_doc_ids = []
        
        for i, title in enumerate(titles):
            if i >= len(sentences_list):
                continue
            
            sentences = sentences_list[i]
            content = " ".join(sentences) if isinstance(sentences, list) else str(sentences)
            
            if not content.strip():
                continue
            
            doc_original_id = f"{original_id}_{title}"
            doc_id = generate_doc_id("2wiki", doc_original_id)
            
            print(f"  翻譯文檔: {title}...")
            translated_content = translate_text(content)
            
            is_gold = title in gold_titles
            docs.append({
                "doc_id": doc_id,
                "content": translated_content,
                "original_source": "2wiki",
                "original_id": doc_original_id,
                "is_gold": is_gold,
            })
            docs_raw.append({
                "doc_id": doc_id,
                "content": content,
                "original_source": "2wiki",
                "original_id": doc_original_id,
                "is_gold": is_gold,
            })
            
            if is_gold:
                gold_doc_ids.append(doc_id)
        
        if not gold_doc_ids:
            continue
        
        # 翻譯問題與答案
        print("  翻譯問題...")
        translated_question = translate_text(item.get("question", ""))
        print("  翻譯答案...")
        translated_answer = translate_text(item.get("answer", ""))
        
        return {
            "query": {
                "question_id": question_id,
                "question": translated_question,
                "gold_answer": translated_answer,
                "gold_doc_ids": gold_doc_ids,
                "source_dataset": "2wiki",
                "question_type": "multi-hop",
            },
            "query_raw": {
                "question_id": question_id,
                "question": item.get("question", ""),
                "gold_answer": item.get("answer", ""),
                "gold_doc_ids": gold_doc_ids,
                "source_dataset": "2wiki",
                "question_type": "multi-hop",
            },
            "docs": docs,
            "docs_raw": docs_raw,
        }
    
    return None


def main():
    if len(sys.argv) < 2:
        print("使用方式: uv run src/replace_question.py <question_id>")
        print("範例: uv run src/replace_question.py e7124c20-75c2-5d99-9acf-d2cba40228fa")
        sys.exit(1)
    
    target_question_id = sys.argv[1]
    
    print("=" * 60)
    print("問題抽換工具")
    print("=" * 60)
    
    # 載入現有資料
    print("\n[1/6] 載入現有資料...")
    queries = load_json(PROCESSED_DIR / "queries.json")
    corpus = load_json(PROCESSED_DIR / "corpus.json")
    queries_raw = load_json(PROCESSED_DIR / "queries_raw.json")
    corpus_raw = load_json(PROCESSED_DIR / "corpus_raw.json")
    
    # 找到要抽換的問題
    target_query = None
    target_index = -1
    for i, q in enumerate(queries):
        if q["question_id"] == target_question_id:
            target_query = q
            target_index = i
            break
    
    if target_query is None:
        print(f"錯誤: 找不到 question_id = {target_question_id}")
        sys.exit(1)
    
    source_dataset = target_query["source_dataset"]
    old_gold_doc_ids = set(target_query["gold_doc_ids"])
    
    print(f"  找到目標問題:")
    print(f"    - ID: {target_question_id}")
    print(f"    - 來源: {source_dataset}")
    print(f"    - 問題: {target_query['question'][:50]}...")
    print(f"    - 黃金文檔數: {len(old_gold_doc_ids)}")
    
    # 載入原始資料
    print(f"\n[2/5] 載入 {source_dataset} 原始資料...")
    if source_dataset == "drcd":
        raw_data = load_json(RAW_DIR / "drcd.json")
    elif source_dataset == "squad":
        raw_data = load_json(RAW_DIR / "squad.json")
    elif source_dataset == "hotpotqa":
        raw_data = load_json(RAW_DIR / "hotpotqa.json")
    elif source_dataset == "2wiki":
        raw_data = load_json(RAW_DIR / "2wiki.json")
    else:
        print(f"錯誤: 不支援的資料集 {source_dataset}")
        sys.exit(1)
    
    # 取得已使用的 contexts 與 question_ids
    used_contexts = get_used_contexts(queries, corpus)
    used_question_ids = get_used_question_ids(queries)
    
    # 提取新的 QA
    print(f"\n[3/6] 從 {source_dataset} 提取新問題...")
    if source_dataset == "drcd":
        new_data = extract_drcd_candidate(raw_data, used_contexts, used_question_ids)
    elif source_dataset == "squad":
        new_data = extract_squad_candidate(raw_data, used_contexts, used_question_ids)
    elif source_dataset == "hotpotqa":
        new_data = extract_hotpotqa_candidate(raw_data, used_contexts, used_question_ids)
    elif source_dataset == "2wiki":
        new_data = extract_2wiki_candidate(raw_data, used_contexts, used_question_ids)
    
    if new_data is None:
        print("錯誤: 找不到可用的替換問題")
        sys.exit(1)
    
    new_query = new_data["query"]
    new_query_raw = new_data.get("query_raw", new_query)
    new_docs = new_data["docs"]
    new_docs_raw = new_data.get("docs_raw", new_docs)
    
    print(f"  新問題:")
    print(f"    - ID: {new_query['question_id']}")
    print(f"    - 問題: {new_query['question'][:50]}...")
    print(f"    - 新增文檔數: {len(new_docs)}")
    
    # 更新 queries
    print(f"\n[4/6] 更新 queries.json...")
    queries[target_index] = new_query
    
    # 更新 queries_raw
    print(f"[5/6] 更新 queries_raw.json...")
    for i, q in enumerate(queries_raw):
        if q["question_id"] == target_question_id:
            queries_raw[i] = new_query_raw
            break
    
    # 更新 corpus
    print(f"[6/6] 更新 corpus.json 與 corpus_raw.json...")
    
    # 移除舊的黃金文檔 (只移除該問題專屬的黃金文檔)
    # 注意: 對於 multi-hop，同時移除 hard negatives
    old_doc_sources = set()
    for doc in corpus:
        if doc["doc_id"] in old_gold_doc_ids:
            old_doc_sources.add(doc.get("original_id", "").split("_")[0] if "_" in doc.get("original_id", "") else doc.get("original_id", ""))
    
    # 對於 single-hop，只移除 gold docs
    # 對於 multi-hop，移除同一個問題的所有相關文檔
    if source_dataset in ["hotpotqa", "2wiki"]:
        # 找出舊問題的所有相關文檔 (根據 original_id 前綴)
        old_question_prefix = None
        for doc in corpus:
            if doc["doc_id"] in old_gold_doc_ids:
                oid = doc.get("original_id", "")
                if "_" in oid:
                    old_question_prefix = oid.rsplit("_", 1)[0]
                    break
        
        if old_question_prefix:
            corpus = [doc for doc in corpus 
                     if not (doc["original_source"] == source_dataset and 
                            doc.get("original_id", "").startswith(old_question_prefix + "_"))]
            corpus_raw = [doc for doc in corpus_raw 
                         if not (doc["original_source"] == source_dataset and 
                                doc.get("original_id", "").startswith(old_question_prefix + "_"))]
        else:
            corpus = [doc for doc in corpus if doc["doc_id"] not in old_gold_doc_ids]
            corpus_raw = [doc for doc in corpus_raw if doc["doc_id"] not in old_gold_doc_ids]
    else:
        corpus = [doc for doc in corpus if doc["doc_id"] not in old_gold_doc_ids]
        corpus_raw = [doc for doc in corpus_raw if doc["doc_id"] not in old_gold_doc_ids]
    
    # 加入新文檔
    corpus.extend(new_docs)
    corpus_raw.extend(new_docs_raw)
    
    # 儲存
    save_json(queries, PROCESSED_DIR / "queries.json")
    save_json(corpus, PROCESSED_DIR / "corpus.json")
    save_json(queries_raw, PROCESSED_DIR / "queries_raw.json")
    save_json(corpus_raw, PROCESSED_DIR / "corpus_raw.json")
    
    print(f"\n{'=' * 60}")
    print("抽換完成！")
    print("=" * 60)
    print(f"  - 舊問題 ID: {target_question_id}")
    print(f"  - 新問題 ID: {new_query['question_id']}")
    print(f"  - 移除文檔數: {len(old_gold_doc_ids) if source_dataset in ['drcd', 'squad'] else '多篇 (含 hard negatives)'}")
    print(f"  - 新增文檔數: {len(new_docs)}")
    print(f"  - 目前 corpus 總數: {len(corpus)}")


if __name__ == "__main__":
    main()
