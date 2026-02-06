"""
翻譯 corpus.json 中新增的未翻譯文檔
"""
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"

client = OpenAI()
MODEL = "gpt-4.1"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def contains_chinese(text: str) -> bool:
    for char in text:
        if '\u4e00' <= char <= '\u9fff':
            return True
    return False

def translate_text(text: str) -> str:
    if not text or not text.strip():
        return text

    system_prompt = """你是專業的英繁翻譯專家。請將以下英文翻譯為台灣繁體中文。
規則：
1. 維持原文的語意和結構
2. 專有名詞保留英文，並在首次出現時加上中文翻譯
3. 使用台灣常用的繁體中文用語
4. 只輸出翻譯結果，不加任何說明"""
    
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

def main():
    corpus = load_json(PROCESSED_DIR / "corpus.json")
    corpus_raw = load_json(PROCESSED_DIR / "corpus_raw.json")
    
    # 找出需要翻譯的文檔 (非 DRCD 但不包含中文)
    to_translate = []
    for i, doc in enumerate(corpus):
        if doc.get("original_source") != "drcd":
            if not contains_chinese(doc.get("content", "")):
                to_translate.append(i)
    
    print(f"需要翻譯的文檔數: {len(to_translate)}")
    
    for idx in to_translate:
        doc = corpus[idx]
        raw_content = corpus_raw[idx].get("content", "")
        
        print(f"翻譯 doc_id: {doc['doc_id'][:30]}...")
        translated = translate_text(raw_content)
        corpus[idx]["content"] = translated
        print(f"  完成 ({len(translated)} 字)")
    
    # 保存
    save_json(PROCESSED_DIR / "corpus.json", corpus)
    print("\n已保存翻譯後的 corpus.json")

if __name__ == "__main__":
    main()
