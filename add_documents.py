"""
從 2wiki 資料集補充 2 個新文檔到 corpus
"""
import json
import uuid
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"
RAW_DIR = BASE_DIR / "data" / "raw"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_doc_id(source: str, original_id: str) -> str:
    combined = f"{source}:{original_id}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, combined))

def main():
    corpus = load_json(PROCESSED_DIR / "corpus.json")
    corpus_raw = load_json(PROCESSED_DIR / "corpus_raw.json")
    
    # 目前使用的 doc_ids 和 original_ids
    used_doc_ids = {d['doc_id'] for d in corpus}
    used_original_ids = {d['original_id'] for d in corpus}
    
    print(f"目前 corpus 數量: {len(corpus)}")
    print(f"需要補充: {600 - len(corpus)} 個文檔")
    
    # 載入 2wiki 原始資料
    wiki2_data = load_json(RAW_DIR / "2wiki.json")
    
    # 找到可用的新文檔
    new_docs = []
    new_docs_raw = []
    
    for item in wiki2_data:
        if len(new_docs) >= 2:
            break
            
        context_data = item.get("context", {})
        titles = context_data.get("title", [])
        sentences_list = context_data.get("sentences", [])
        original_id = item.get("id", "")
        
        for i, title in enumerate(titles):
            if len(new_docs) >= 2:
                break
                
            if i >= len(sentences_list):
                continue
                
            sentences = sentences_list[i]
            content = " ".join(sentences) if isinstance(sentences, list) else str(sentences)
            
            if not content.strip():
                continue
            
            doc_original_id = f"{original_id}_{title}"
            doc_id = generate_doc_id("2wiki", doc_original_id)
            
            # 確保未使用過
            if doc_id in used_doc_ids or doc_original_id in used_original_ids:
                continue
            
            # 新增文檔
            new_docs.append({
                "doc_id": doc_id,
                "content": content,  # 這裡應該翻譯，但保持原文以便後續處理
                "original_source": "2wiki",
                "original_id": doc_original_id,
                "is_gold": False,
            })
            new_docs_raw.append({
                "doc_id": doc_id,
                "content": content,
                "original_source": "2wiki",
                "original_id": doc_original_id,
                "is_gold": False,
            })
            
            used_doc_ids.add(doc_id)
            used_original_ids.add(doc_original_id)
            
            print(f"新增文檔: {doc_id[:20]}... | {title[:30]}...")
    
    # 合併
    corpus.extend(new_docs)
    corpus_raw.extend(new_docs_raw)
    
    print(f"\n更新後 corpus 數量: {len(corpus)}")
    
    # 保存
    save_json(PROCESSED_DIR / "corpus.json", corpus)
    save_json(PROCESSED_DIR / "corpus_raw.json", corpus_raw)
    print("已保存更新後的檔案")
    
    # 提示需要翻譯
    if new_docs:
        print("\n⚠️ 新增的文檔尚未翻譯，請執行 translate_data.py 進行翻譯")
        print("或手動翻譯以下 doc_id 的 content:")
        for d in new_docs:
            print(f"  - {d['doc_id']}")

if __name__ == "__main__":
    main()
