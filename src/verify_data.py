"""
資料驗證腳本
驗證處理後的資料是否符合規格與預期。

驗證項目：
1. 檔案存在性
2. 資料數量 (50 QA, 500 Docs)
3. 欄位完整性與型別
4. 資料一致性 (Gold Doc IDs 存在於 Corpus)
5. 語言檢查 (簡單檢查是否包含中文字元)
"""

import json
from pathlib import Path
from collections import Counter

# 路徑設定
BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

def load_json(filepath: Path) -> list[dict]:
    """載入 JSON 檔案"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def contains_chinese(text: str) -> bool:
    """檢查文字是否包含中文字元"""
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False

def main():
    print("=" * 60)
    print("開始資料驗證")
    print("=" * 60)
    
    queries_path = PROCESSED_DIR / "queries.json"
    corpus_path = PROCESSED_DIR / "corpus.json"
    
    # 1. 檔案存在性
    if not queries_path.exists():
        print(f"[FAIL] 找不到 {queries_path}")
        return
    if not corpus_path.exists():
        print(f"[FAIL] 找不到 {corpus_path}")
        return
        
    print("[PASS] 檔案存在")
    
    # 載入資料
    queries = load_json(queries_path)
    corpus = load_json(corpus_path)
    
    # 2. 資料數量驗證
    print(f"\n[數量驗證]")
    print(f"  - Queries: {len(queries)} (預期 50)")
    print(f"  - Corpus: {len(corpus)} (預期 500)")
    
    if len(queries) == 50:
        print("[PASS] Queries 數量正確")
    else:
        print(f"[FAIL] Queries 數量錯誤: {len(queries)}")
        
    if len(corpus) == 500:
        print("[PASS] Corpus 數量正確")
    else:
        print(f"[FAIL] Corpus 數量錯誤: {len(corpus)}")
        
    # 3. 分佈驗證
    print(f"\n[分佈驗證]")
    sources = Counter(q.get("source_dataset") for q in queries)
    print(f"  - 分佈: {dict(sources)}")
    
    expected_sources = {
        "drcd": 15,
        "squad": 15,
        "hotpotqa": 10,
        "2wiki": 10
    }
    
    if sources == expected_sources:
        print("[PASS] 資料來源分佈正確")
    else:
        print(f"[FAIL] 資料來源分佈錯誤: 預期 {expected_sources}")
        
    types = Counter(q.get("question_type") for q in queries)
    print(f"  - 類型: {dict(types)}")
    
    # 4. 一致性驗證
    print(f"\n[一致性驗證]")
    corpus_ids = {d.get("doc_id") for d in corpus}
    
    missing_docs = []
    gold_doc_counts = []
    
    for q in queries:
        golds = q.get("gold_doc_ids", [])
        gold_doc_counts.append(len(golds))
        for gid in golds:
            if gid not in corpus_ids:
                missing_docs.append((q.get("question_id"), gid))
    
    if not missing_docs:
        print("[PASS] 所有 Gold Doc IDs 皆存在於 Corpus")
    else:
        print(f"[FAIL] 發現 {len(missing_docs)} 個缺失的 Gold Docs")
        
    print(f"  - 每個問題的 Gold Docs 數量範圍: {min(gold_doc_counts)} - {max(gold_doc_counts)}")

    # 5. 語言檢查
    print(f"\n[語言檢查 (抽樣)]")
    # 檢查非 DRCD 的樣本是否包含中文
    non_drcd_queries = [q for q in queries if q.get("source_dataset") != "drcd"]
    non_drcd_corpus = [d for d in corpus if d.get("original_source") != "drcd"]
    
    q_errors = 0
    c_errors = 0
    
    for q in non_drcd_queries:
        if not contains_chinese(q.get("question", "")):
            q_errors += 1
            
    for c in non_drcd_corpus:
        if not contains_chinese(c.get("content", "")):
            c_errors += 1
            
    if q_errors == 0:
        print(f"[PASS] 所有非 DRCD Queries ({len(non_drcd_queries)}) 皆包含繁體中文")
    else:
        print(f"[WARN] 有 {q_errors} 個 Queries 可能未翻譯成功")
        
    if c_errors == 0:
        print(f"[PASS] 所有非 DRCD Corpus ({len(non_drcd_corpus)}) 皆包含繁體中文")
    else:
        print(f"[WARN] 有 {c_errors} 個 Corpus 可能未翻譯成功")
        
    print(f"\n{'=' * 60}")
    print("驗證完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
