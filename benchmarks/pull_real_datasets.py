import json
from datasets import load_dataset
from pathlib import Path

DATA_DIR = Path(__file__).parent / "eval_datasets"

def main():
    # 1. Prompt Injection (deepset/prompt-injections)
    print("Pulling deepset/prompt-injections...")
    ds_inj = load_dataset("deepset/prompt-injections", split="train")
    
    inj_records = []
    for row in ds_inj:
        inj_records.append({
            "prompt": row["text"],
            "is_injection": row["label"] == 1
        })
    
    with open(DATA_DIR / "injection_v1.jsonl", "w") as f:
        for r in inj_records:
            f.write(json.dumps(r) + "\n")
    print(f"Wrote {len(inj_records)} real injection records.")

    # 2. Faithfulness (pminervini/HaluEval)
    print("Pulling pminervini/HaluEval (qa split)...")
    try:
        ds_faith = load_dataset("pminervini/HaluEval", "qa", split="data")
        
        faith_records = []
        for row in ds_faith:
            context = f"{row.get('knowledge', '')}\n\nQuestion: {row.get('question', '')}"
            
            # Add one faithful record
            faith_records.append({
                "context": context,
                "claim": row.get('right_answer', ''),
                "is_faithful": True
            })
            
            # Add one hallucinated record
            faith_records.append({
                "context": context,
                "claim": row.get('hallucinated_answer', ''),
                "is_faithful": False
            })
            
        with open(DATA_DIR / "faithfulness_v1.jsonl", "w") as f:
            for r in faith_records:
                f.write(json.dumps(r) + "\n")
        print(f"Wrote {len(faith_records)} real faithfulness records.")
    except Exception as e:
        print(f"Error loading HaluEval dataset: {e}")

if __name__ == "__main__":
    main()
