import json
from pathlib import Path

from datasets import load_dataset

DATA_DIR = Path(__file__).parent / "eval_datasets"


def main():
    # 1. Prompt Injection (deepset/prompt-injections)
    ds_inj = load_dataset("deepset/prompt-injections", split="train")

    inj_records = []
    for row in ds_inj:
        inj_records.append({"prompt": row["text"], "is_injection": row["label"] == 1})

    with open(DATA_DIR / "injection_v1.jsonl", "w") as f:
        for r in inj_records:
            f.write(json.dumps(r) + "\n")

    # 2. Faithfulness (pminervini/HaluEval)
    try:
        ds_faith = load_dataset("pminervini/HaluEval", "qa", split="data")

        faith_records = []
        for row in ds_faith:
            context = f"{row.get('knowledge', '')}\n\nQuestion: {row.get('question', '')}"

            # Add one faithful record
            faith_records.append({"context": context, "claim": row.get("right_answer", ""), "is_faithful": True})

            # Add one hallucinated record
            faith_records.append({"context": context, "claim": row.get("hallucinated_answer", ""), "is_faithful": False})

        with open(DATA_DIR / "faithfulness_v1.jsonl", "w") as f:
            for r in faith_records:
                f.write(json.dumps(r) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
