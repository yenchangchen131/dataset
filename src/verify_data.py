"""
資料驗證腳本
驗證處理後的資料是否符合規格與預期。

驗證項目：
1. 檔案存在性
2. 資料數量 (60 QA, 600 Docs)
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

# 預期值配置
EXPECTED_QUERIES = 60
EXPECTED_CORPUS = 600
EXPECTED_DISTRIBUTION = {
    "drcd": 20,
    "hotpotqa": 20,
    "2wiki": 20
}

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
    
    # 檔案路徑定義
    files = {
        "queries": PROCESSED_DIR / "queries.json",
        "corpus": PROCESSED_DIR / "corpus.json",
        "queries_raw": PROCESSED_DIR / "queries_raw.json",
        "corpus_raw": PROCESSED_DIR / "corpus_raw.json"
    }
    
    # 載入資料
    data = {}
    print("[1. 檔案存在性檢查]")
    for name, path in files.items():
        if path.exists():
            print(f"  [PASS] {name} 存在")
            try:
                data[name] = load_json(path)
            except Exception as e:
                print(f"  [FAIL] {name} 讀取失敗: {e}")
        else:
            print(f"  [WARN] {name} 不存在 (部分驗證將跳過)")
            
    # Processed Data 驗證
    queries = data.get("queries")
    corpus = data.get("corpus")
    
    if queries:
        print(f"\n[Processed Queries 驗證]")
        # 數量
        if len(queries) == EXPECTED_QUERIES:
            print(f"  [PASS] 數量正確: {len(queries)}")
        else:
            print(f"  [FAIL] 數量錯誤: {len(queries)} (預期 {EXPECTED_QUERIES})")
            
        # 分佈
        sources = Counter(q.get("source_dataset") for q in queries)
        if sources == EXPECTED_DISTRIBUTION:
            print(f"  [PASS] 來源分佈正確: {dict(sources)}")
        else:
            print(f"  [FAIL] 來源分佈錯誤: {dict(sources)}")
            
        # 重複性
        q_ids = [q['question_id'] for q in queries]
        dup_q_ids = [item for item, count in Counter(q_ids).items() if count > 1]
        if not dup_q_ids:
            print("  [PASS] 無重複 ID")
        else:
            print(f"  [FAIL] 發現 {len(dup_q_ids)} 個重複 ID")
            
        # 語言檢查 (非 DRCD)
        q_errors = 0
        non_drcd = [q for q in queries if q.get("source_dataset") != "drcd"]
        for q in non_drcd:
            if not contains_chinese(q.get("question", "")):
                q_errors += 1
        if q_errors == 0:
            print(f"  [PASS] 非 DRCD 問題皆包含中文 ({len(non_drcd)} 題)")
        else:
            print(f"  [WARN] {q_errors} 題可能未翻譯")

    if corpus:
        print(f"\n[Processed Corpus 驗證]")
        # 數量
        if len(corpus) == EXPECTED_CORPUS:
            print(f"  [PASS] 數量正確: {len(corpus)}")
        else:
            print(f"  [FAIL] 數量錯誤: {len(corpus)} (預期 {EXPECTED_CORPUS})")
            
        # 重複性檢查
        doc_ids = [d['doc_id'] for d in corpus]
        dup_doc_ids = [item for item, count in Counter(doc_ids).items() if count > 1]
        if not dup_doc_ids:
            print(f"  [PASS] 無重複 doc_id ({len(set(doc_ids))} unique)")
        else:
            print(f"  [FAIL] 發現 {len(dup_doc_ids)} 個重複 doc_id:")
            for did in dup_doc_ids:
                print(f"    - {did}")
            
        # 語言檢查
        c_errors = 0
        non_drcd = [d for d in corpus if d.get("original_source") != "drcd"]
        for c in non_drcd:
            if not contains_chinese(c.get("content", "")):
                c_errors += 1
        if c_errors == 0:
            print(f"  [PASS] 非 DRCD 文檔皆包含中文 ({len(non_drcd)} 篇)")
        else:
            print(f"  [WARN] {c_errors} 篇可能未翻譯")
            
    # Processed 一致性 (需兩者都在)
    if queries and corpus:
        print(f"\n[Processed 一致性驗證]")
        corpus_ids = {d.get("doc_id") for d in corpus}
        missing_docs = []
        for q in queries:
            for gid in q.get("gold_doc_ids", []):
                if gid not in corpus_ids:
                    missing_docs.append((q.get("question_id"), gid))
        
        if not missing_docs:
            print("  [PASS] 所有 Gold Doc IDs 皆存在於 Corpus")
        else:
            print(f"  [FAIL] 發現 {len(missing_docs)} 個缺失文檔")

    # Raw Data 驗證
    queries_raw = data.get("queries_raw")
    corpus_raw = data.get("corpus_raw")
    
    if queries_raw:
        print(f"\n[Raw Queries 驗證]")
        if len(queries_raw) == EXPECTED_QUERIES:
            print(f"  [PASS] 數量正確: {len(queries_raw)}")
        else:
            print(f"  [FAIL] 數量錯誤: {len(queries_raw)}")
            
        # 重複性
        q_raw_ids = [q['question_id'] for q in queries_raw]
        dup_raw = [item for item, count in Counter(q_raw_ids).items() if count > 1]
        if not dup_raw:
            print("  [PASS] 無重複 ID")
        else:
            print(f"  [FAIL] 發現 {len(dup_raw)} 個重複 ID")
            
    if corpus_raw:
        print(f"\n[Raw Corpus 驗證]")
        if len(corpus_raw) == EXPECTED_CORPUS:
            print(f"  [PASS] 數量正確: {len(corpus_raw)}")
        else:
            print(f"  [FAIL] 數量錯誤: {len(corpus_raw)}")

    # Raw vs Processed 一致性
    if queries and queries_raw:
        print(f"\n[Queries vs Raw 一致性]")
        if len(queries) == len(queries_raw):
            print("  [PASS] 數量一致")
        else:
            print(f"  [FAIL] 數量不一致 ({len(queries)} vs {len(queries_raw)})")
            
        q_ids = set(q['question_id'] for q in queries)
        r_ids = set(q['question_id'] for q in queries_raw)
        if q_ids == r_ids:
            print("  [PASS] ID 集合一致")
        else:
            print("  [FAIL] ID 集合不一致")
            
    if corpus and corpus_raw:
        print(f"\n[Corpus vs Raw 一致性]")
        if len(corpus) == len(corpus_raw):
            print("  [PASS] 數量一致")
        else:
            print(f"  [FAIL] 數量不一致 ({len(corpus)} vs {len(corpus_raw)})")

    print(f"\n{'=' * 60}")
    print("驗證完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
