"""
移除 corpus.json 中的重複 doc_id，並從同資料集找取代文檔
"""
import json
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    corpus_path = PROCESSED_DIR / "corpus.json"
    corpus_raw_path = PROCESSED_DIR / "corpus_raw.json"
    
    corpus = load_json(corpus_path)
    corpus_raw = load_json(corpus_raw_path)
    
    # 找出重複的 doc_id
    doc_ids = [d['doc_id'] for d in corpus]
    dup_ids = [k for k, v in Counter(doc_ids).items() if v > 1]
    
    print(f"發現 {len(dup_ids)} 個重複的 doc_id:")
    for did in dup_ids:
        # 找到所有重複項
        matches = [(i, d) for i, d in enumerate(corpus) if d['doc_id'] == did]
        print(f"  {did}:")
        for idx, doc in matches:
            print(f"    [idx={idx}] source={doc['original_source']}, original_id={doc['original_id']}")
    
    # 移除重複項 (保留第一個)
    seen = set()
    new_corpus = []
    new_corpus_raw = []
    removed_indices = []
    
    for i, doc in enumerate(corpus):
        if doc['doc_id'] in seen:
            removed_indices.append(i)
            print(f"\n移除重複項 idx={i}: {doc['doc_id']}")
        else:
            seen.add(doc['doc_id'])
            new_corpus.append(doc)
            new_corpus_raw.append(corpus_raw[i])
    
    print(f"\n移除後: {len(new_corpus)} 文檔 (原有 {len(corpus)})")
    
    # 保存
    save_json(corpus_path, new_corpus)
    save_json(corpus_raw_path, new_corpus_raw)
    print("已保存更新後的 corpus.json 和 corpus_raw.json")

if __name__ == "__main__":
    main()
