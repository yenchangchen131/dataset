import os
import json
from pathlib import Path
from datasets import load_dataset

"""
說明: 
    此腳本負責下載 RAG 評測所需的原始資料集 (Raw Datasets)。
    1. 強制轉存為 'Standard JSON Array' 格式 ([{},{}])，
       避免 HuggingFace 預設的 JSON Lines 導致讀取錯誤。
    
資料集清單:
    1. DRCD (Test)
    2. HotpotQA (Distractor/Validation)
    3. 2WikiMultiHopQA (Validation)
"""

# --- 1. 路徑設定 (Path Configuration) ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# 建議將原始檔存放在 data/raw 以便管理
DATA_DIR = PROJECT_ROOT / "data" / "raw"

# 確保資料夾存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
print(f"📂 原始資料儲存路徑: {DATA_DIR}")

# --- 2. 資料集清單設定 (Dataset Config) ---
TARGET_DATASETS = {
    # [Single-hop] DRCD
    "drcd": ("voidful/drcd", None, "test"),

    # [Multi-hop] HotpotQA
    "hotpotqa": ("hotpotqa/hotpot_qa", "distractor", "validation"),

    # [Multi-hop] 2WikiMultiHopQA
    "2wiki": ("framolfese/2WikiMultihopQA", None, "validation"),
}

# --- 3. 下載與儲存邏輯 (Download & Save) ---
def download_and_save():
    print("🚀 開始下載資料集...\n")
    
    for filename, (hf_id, config, split) in TARGET_DATASETS.items():
        save_path = DATA_DIR / f"{filename}.json"
        
        if save_path.exists():
            print(f"⚠️  {filename}.json 已存在，跳過下載。")
            continue

        print(f"⬇️  正在下載: {hf_id} (Config: {config}, Split: {split})...")
        
        try:
            # 1. 載入資料集
            if config:
                ds = load_dataset(hf_id, config, split=split)
            else:
                ds = load_dataset(hf_id, split=split)
            
            print(f"   ✅ 下載完成！筆數: {len(ds)}")
            print(f"   🔄 正在轉換為標準 JSON Array 格式...")

            # 2. 轉換格式
            # ds.to_list() 會將整個資料集轉為 Python List of Dicts
            # 這樣可以確保 json.dump 寫入時會包含最外層的 '[]'
            data_list = ds.to_list()

            print(f"   💾 正在儲存至: {save_path.name} ...")
            
            # 3. 寫入檔案
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(
                    data_list, 
                    f, 
                    ensure_ascii=False, # 確保中文不被轉碼
                    indent=2            # 縮排，方便人類閱讀
                )
            
            print(f"   🎉 {filename} 處理完畢！\n")
            
        except Exception as e:
            print(f"❌ {filename} 下載失敗: {e}")
            print("   (請檢查網路連線或 HuggingFace ID 是否變動)\n")

if __name__ == "__main__":
    download_and_save()
    print("-" * 30)
    print(f"✅ 所有任務完成！原始資料位於: {DATA_DIR}")