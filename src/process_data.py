"""
資料提取與處理腳本
從四個原始資料集 (DRCD, SQuAD, HotpotQA, 2WikiMultiHopQA) 中採樣並組裝文檔池。

輸出：
- data/processed/queries_raw.json: 50 筆 QA 對
- data/processed/corpus_raw.json: 500 篇文檔
"""

import json
import uuid
import random
from pathlib import Path
from typing import Any

# 設定隨機種子以確保可重現性
random.seed(11)

# 路徑設定
BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# 採樣配置 (移除 SQuAD，共 60 題)
SAMPLING_CONFIG = {
    "drcd": {"count": 20, "type": "single-hop"},
    "hotpotqa": {"count": 20, "type": "multi-hop"},
    "2wiki": {"count": 20, "type": "multi-hop"},
}

TOTAL_CORPUS_SIZE = 600


def generate_doc_id(source: str, original_id: str) -> str:
    """生成唯一的文檔 ID"""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{source}:{original_id}"))


def generate_question_id(source: str, original_id: str) -> str:
    """生成唯一的問題 ID"""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"q:{source}:{original_id}"))


def load_json(filepath: Path) -> list[dict]:
    """載入 JSON 檔案"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: list[dict], filepath: Path) -> None:
    """儲存 JSON 檔案"""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def process_drcd(data: list[dict], count: int) -> tuple[list[dict], list[dict], set[str]]:
    """
    處理 DRCD 資料集
    結構: [{title, paragraphs: [{context, qas: [{question, answers, id}]}]}]
    
    Returns:
        queries: QA 列表
        gold_docs: 黃金文檔列表
        used_contexts: 已使用的 context 集合
    """
    queries = []
    gold_docs = []
    used_contexts: set[str] = set()
    
    # 展平所有 QA 對並記錄其 context
    all_qas = []
    for article in data:
        for para in article.get("paragraphs", []):
            context = para.get("context", "")
            if not context or context in used_contexts:
                continue
            for qa in para.get("qas", []):
                all_qas.append({
                    "qa": qa,
                    "context": context,
                    "title": article.get("title", ""),
                })
    
    # 隨機打亂並選取（確保每個 context 只選一個 QA）
    random.shuffle(all_qas)
    
    for item in all_qas:
        if len(queries) >= count:
            break
        
        context = item["context"]
        if context in used_contexts:
            continue
        
        qa = item["qa"]
        original_id = qa.get("id", str(uuid.uuid4()))
        doc_id = generate_doc_id("drcd", original_id)
        question_id = generate_question_id("drcd", original_id)
        
        # 取得答案文字
        answers = qa.get("answers", [])
        answer_text = answers[0].get("text", "") if answers else ""
        
        gold_docs.append({
            "doc_id": doc_id,
            "content": context,
            "original_source": "drcd",
            "original_id": original_id,
            "is_gold": True,
        })
        
        queries.append({
            "question_id": question_id,
            "question": qa.get("question", ""),
            "gold_answer": answer_text,
            "gold_doc_ids": [doc_id],
            "source_dataset": "drcd",
            "question_type": "single-hop",
        })
        
        used_contexts.add(context)
    
    print(f"[DRCD] 提取 {len(queries)} 題 QA, {len(gold_docs)} 篇黃金文檔")
    return queries, gold_docs, used_contexts


def process_squad(data: list[dict], count: int) -> tuple[list[dict], list[dict], set[str]]:
    """
    處理 SQuAD 資料集
    結構: [{id, title, context, question, answers: {text: [], answer_start: []}}]
    """
    queries = []
    gold_docs = []
    used_contexts: set[str] = set()
    
    # 按 context 分組，每個 context 只選一個 QA
    context_to_qas: dict[str, list[dict]] = {}
    for item in data:
        context = item.get("context", "")
        if not context:
            continue
        if context not in context_to_qas:
            context_to_qas[context] = []
        context_to_qas[context].append(item)
    
    # 隨機選取 contexts
    contexts = list(context_to_qas.keys())
    random.shuffle(contexts)
    
    for context in contexts:
        if len(queries) >= count:
            break
        
        # 從該 context 隨機選一個 QA
        qa_item = random.choice(context_to_qas[context])
        original_id = qa_item.get("id", str(uuid.uuid4()))
        doc_id = generate_doc_id("squad", original_id)
        question_id = generate_question_id("squad", original_id)
        
        # 取得答案文字
        answers = qa_item.get("answers", {})
        answer_texts = answers.get("text", [])
        answer_text = answer_texts[0] if answer_texts else ""
        
        gold_docs.append({
            "doc_id": doc_id,
            "content": context,
            "original_source": "squad",
            "original_id": original_id,
            "is_gold": True,
        })
        
        queries.append({
            "question_id": question_id,
            "question": qa_item.get("question", ""),
            "gold_answer": answer_text,
            "gold_doc_ids": [doc_id],
            "source_dataset": "squad",
            "question_type": "single-hop",
        })
        
        used_contexts.add(context)
    
    print(f"[SQuAD] 提取 {len(queries)} 題 QA, {len(gold_docs)} 篇黃金文檔")
    return queries, gold_docs, used_contexts


def process_hotpotqa(data: list[dict], count: int) -> tuple[list[dict], list[dict], list[dict], set[str]]:
    """
    處理 HotpotQA 資料集
    結構: [{id, question, answer, supporting_facts: {title, sent_id}, 
            context: {title: [], sentences: [[sent1, sent2, ...], ...]}}]
    
    Returns:
        queries: QA 列表
        gold_docs: 黃金文檔列表
        hard_negatives: 困難負樣本列表
        used_contexts: 已使用的 context 集合
    """
    queries = []
    gold_docs = []
    hard_negatives = []
    used_contexts: set[str] = set()
    
    # 隨機打亂
    data_copy = data.copy()
    random.shuffle(data_copy)
    
    for item in data_copy:
        if len(queries) >= count:
            break
        
        original_id = item.get("id", str(uuid.uuid4()))
        question_id = generate_question_id("hotpotqa", original_id)
        
        # 解析 context
        context_data = item.get("context", {})
        titles = context_data.get("title", [])
        sentences_list = context_data.get("sentences", [])
        
        # 解析 supporting_facts
        supporting_facts = item.get("supporting_facts", {})
        gold_titles = set(supporting_facts.get("title", []))
        
        # 建立 title -> doc 的映射
        gold_doc_ids = []
        question_used_contexts = []
        
        for i, title in enumerate(titles):
            if i >= len(sentences_list):
                continue
            
            # 合併句子為完整段落
            sentences = sentences_list[i]
            content = " ".join(sentences) if isinstance(sentences, list) else str(sentences)
            
            if not content.strip():
                continue
            
            doc_original_id = f"{original_id}_{title}"
            doc_id = generate_doc_id("hotpotqa", doc_original_id)
            
            if content in used_contexts:
                # 如果 context 已被使用，跳過此問題
                continue
            
            doc = {
                "doc_id": doc_id,
                "content": content,
                "original_source": "hotpotqa",
                "original_id": doc_original_id,
                "is_gold": title in gold_titles,
            }
            
            if title in gold_titles:
                gold_docs.append(doc)
                gold_doc_ids.append(doc_id)
            else:
                hard_negatives.append(doc)
            
            question_used_contexts.append(content)
        
        # 只有當有黃金文檔時才添加問題
        if gold_doc_ids:
            queries.append({
                "question_id": question_id,
                "question": item.get("question", ""),
                "gold_answer": item.get("answer", ""),
                "gold_doc_ids": gold_doc_ids,
                "source_dataset": "hotpotqa",
                "question_type": "multi-hop",
            })
            used_contexts.update(question_used_contexts)
    
    print(f"[HotpotQA] 提取 {len(queries)} 題 QA, {len(gold_docs)} 篇黃金文檔, {len(hard_negatives)} 篇困難負樣本")
    return queries, gold_docs, hard_negatives, used_contexts


def process_2wiki(data: list[dict], count: int) -> tuple[list[dict], list[dict], list[dict], set[str]]:
    """
    處理 2WikiMultiHopQA 資料集
    結構類似 HotpotQA
    """
    queries = []
    gold_docs = []
    hard_negatives = []
    used_contexts: set[str] = set()
    
    # 隨機打亂
    data_copy = data.copy()
    random.shuffle(data_copy)
    
    for item in data_copy:
        if len(queries) >= count:
            break
        
        original_id = item.get("id", str(uuid.uuid4()))
        question_id = generate_question_id("2wiki", original_id)
        
        # 解析 context
        context_data = item.get("context", {})
        titles = context_data.get("title", [])
        sentences_list = context_data.get("sentences", [])
        
        # 解析 supporting_facts
        supporting_facts = item.get("supporting_facts", {})
        gold_titles = set(supporting_facts.get("title", []))
        
        # 建立 title -> doc 的映射
        gold_doc_ids = []
        question_used_contexts = []
        
        for i, title in enumerate(titles):
            if i >= len(sentences_list):
                continue
            
            # 合併句子為完整段落
            sentences = sentences_list[i]
            content = " ".join(sentences) if isinstance(sentences, list) else str(sentences)
            
            if not content.strip():
                continue
            
            doc_original_id = f"{original_id}_{title}"
            doc_id = generate_doc_id("2wiki", doc_original_id)
            
            if content in used_contexts:
                continue
            
            doc = {
                "doc_id": doc_id,
                "content": content,
                "original_source": "2wiki",
                "original_id": doc_original_id,
                "is_gold": title in gold_titles,
            }
            
            if title in gold_titles:
                gold_docs.append(doc)
                gold_doc_ids.append(doc_id)
            else:
                hard_negatives.append(doc)
            
            question_used_contexts.append(content)
        
        # 只有當有黃金文檔時才添加問題
        if gold_doc_ids:
            queries.append({
                "question_id": question_id,
                "question": item.get("question", ""),
                "gold_answer": item.get("answer", ""),
                "gold_doc_ids": gold_doc_ids,
                "source_dataset": "2wiki",
                "question_type": "multi-hop",
            })
            used_contexts.update(question_used_contexts)
    
    print(f"[2Wiki] 提取 {len(queries)} 題 QA, {len(gold_docs)} 篇黃金文檔, {len(hard_negatives)} 篇困難負樣本")
    return queries, gold_docs, hard_negatives, used_contexts


def collect_random_negatives(
    squad_data: list[dict],
    drcd_data: list[dict],
    used_contexts: set[str],
    target_count: int
) -> list[dict]:
    """
    從未使用的 SQuAD/DRCD contexts 中收集隨機負樣本
    """
    random_negatives = []
    
    # 從 SQuAD 收集
    for item in squad_data:
        context = item.get("context", "")
        if context and context not in used_contexts:
            doc_id = generate_doc_id("squad", f"neg_{len(random_negatives)}")
            random_negatives.append({
                "doc_id": doc_id,
                "content": context,
                "original_source": "squad",
                "original_id": item.get("id", ""),
                "is_gold": False,
            })
            used_contexts.add(context)
    
    # 從 DRCD 收集
    for article in drcd_data:
        for para in article.get("paragraphs", []):
            context = para.get("context", "")
            if context and context not in used_contexts:
                doc_id = generate_doc_id("drcd", f"neg_{len(random_negatives)}")
                random_negatives.append({
                    "doc_id": doc_id,
                    "content": context,
                    "original_source": "drcd",
                    "original_id": para.get("id", ""),
                    "is_gold": False,
                })
                used_contexts.add(context)
    
    # 隨機打亂並取需要的數量
    random.shuffle(random_negatives)
    return random_negatives[:target_count]


def collect_random_negatives_drcd_only(
    drcd_data: list[dict],
    used_contexts: set[str],
    target_count: int
) -> list[dict]:
    """
    從未使用的 DRCD contexts 中收集隨機負樣本
    """
    random_negatives = []
    
    for article in drcd_data:
        for para in article.get("paragraphs", []):
            context = para.get("context", "")
            if context and context not in used_contexts:
                doc_id = generate_doc_id("drcd", f"neg_{len(random_negatives)}")
                random_negatives.append({
                    "doc_id": doc_id,
                    "content": context,
                    "original_source": "drcd",
                    "original_id": para.get("id", ""),
                    "is_gold": False,
                })
                used_contexts.add(context)
    
    # 隨機打亂並取需要的數量
    random.shuffle(random_negatives)
    return random_negatives[:target_count]


def main():
    print("=" * 60)
    print("開始資料提取與處理")
    print("=" * 60)
    
    # 載入原始資料
    print("\n[1/4] 載入原始資料...")
    drcd_data = load_json(RAW_DIR / "drcd.json")
    hotpotqa_data = load_json(RAW_DIR / "hotpotqa.json")
    wiki2_data = load_json(RAW_DIR / "2wiki.json")
    
    print(f"  - DRCD: {len(drcd_data)} 篇文章")
    print(f"  - HotpotQA: {len(hotpotqa_data)} 筆記錄")
    print(f"  - 2Wiki: {len(wiki2_data)} 筆記錄")
    
    # 處理各資料集
    print("\n[2/4] 處理 DRCD...")
    drcd_queries, drcd_gold_docs, drcd_used = process_drcd(
        drcd_data, SAMPLING_CONFIG["drcd"]["count"]
    )
    
    print("\n[3/4] 處理 HotpotQA...")
    hotpot_queries, hotpot_gold_docs, hotpot_hard_negs, hotpot_used = process_hotpotqa(
        hotpotqa_data, SAMPLING_CONFIG["hotpotqa"]["count"]
    )
    
    print("\n[4/4] 處理 2WikiMultiHopQA...")
    wiki2_queries, wiki2_gold_docs, wiki2_hard_negs, wiki2_used = process_2wiki(
        wiki2_data, SAMPLING_CONFIG["2wiki"]["count"]
    )
    
    # 合併所有 queries
    all_queries = drcd_queries + hotpot_queries + wiki2_queries
    
    # 合併所有文檔
    all_gold_docs = drcd_gold_docs + hotpot_gold_docs + wiki2_gold_docs
    all_hard_negatives = hotpot_hard_negs + wiki2_hard_negs
    
    # 記錄所有已使用的 contexts
    all_used_contexts = drcd_used | hotpot_used | wiki2_used
    
    # 計算需要多少隨機負樣本
    current_corpus_size = len(all_gold_docs) + len(all_hard_negatives)
    needed_random_negs = TOTAL_CORPUS_SIZE - current_corpus_size
    
    print(f"\n[組裝文檔池]")
    print(f"  - 黃金文檔: {len(all_gold_docs)} 篇")
    print(f"  - 困難負樣本: {len(all_hard_negatives)} 篇")
    print(f"  - 需要隨機負樣本: {needed_random_negs} 篇")
    
    # 收集隨機負樣本 (只從 DRCD 收集，因為已移除 SQuAD)
    if needed_random_negs > 0:
        random_negatives = collect_random_negatives_drcd_only(
            drcd_data, all_used_contexts, needed_random_negs
        )
        print(f"  - 收集到隨機負樣本: {len(random_negatives)} 篇")
    else:
        random_negatives = []
    
    # 組裝最終文檔池
    all_corpus = all_gold_docs + all_hard_negatives + random_negatives
    
    # 打亂文檔順序
    random.shuffle(all_corpus)
    
    # 輸出統計
    print(f"\n{'=' * 60}")
    print("最終統計")
    print("=" * 60)
    print(f"總 QA 數量: {len(all_queries)}")
    print(f"  - DRCD (繁中/單跳): {len(drcd_queries)}")
    print(f"  - HotpotQA (英文/多跳): {len(hotpot_queries)}")
    print(f"  - 2Wiki (英文/多跳): {len(wiki2_queries)}")
    print(f"\n總文檔數量: {len(all_corpus)}")
    
    gold_count = sum(1 for d in all_corpus if d.get("is_gold"))
    print(f"  - 黃金文檔 (is_gold=True): {gold_count}")
    print(f"  - 其他文檔 (is_gold=False): {len(all_corpus) - gold_count}")
    
    # 儲存輸出
    print(f"\n[儲存輸出]")
    save_json(all_queries, PROCESSED_DIR / "queries_raw.json")
    save_json(all_corpus, PROCESSED_DIR / "corpus_raw.json")
    print(f"  - 已儲存: {PROCESSED_DIR / 'queries_raw.json'}")
    print(f"  - 已儲存: {PROCESSED_DIR / 'corpus_raw.json'}")
    
    print(f"\n{'=' * 60}")
    print("處理完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
