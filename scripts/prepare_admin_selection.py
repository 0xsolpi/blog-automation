#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--input", default=str(ROOT / "data" / "trends" / "luffy2_mentions.curated.json"))
    args = ap.parse_args()

    inp = Path(args.input)
    src = json.loads(inp.read_text(encoding="utf-8"))
    items = src.get("items", [])

    out_dir = ROOT / "data" / "handoff" / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    candidates = {
        "run_id": args.run_id,
        "from": "luffy",
        "to": "nere",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "items": [
            {
                "rank": i + 1,
                "candidate_name": it.get("product_name", ""),
                "candidate_brand": it.get("product_brand", ""),
                "candidate_model": it.get("product_model", ""),
                "category": it.get("product_category", ""),
                "issue_reason": it.get("mentioned_content", ""),
                "source": it.get("source", ""),
                "mention_type": it.get("mention_type", ""),
                "evidence_link": it.get("related_link", ""),
                "score": it.get("score", 0),
            }
            for i, it in enumerate(items)
        ],
    }

    admin_select = {
        "run_id": args.run_id,
        "from": "admin",
        "to": "ace",
        "generated_at": "",
        "selected_items": [
            {
                "rank": "",
                "product_name": "",
                "product_brand": "",
                "product_model": "",
                "category": "",
                "selection_note": "",
                "evidence_link": "",
            }
        ],
        "note": "Admin가 nere_to_admin_candidates.json을 보고 확정한 제품/모델만 기입",
    }

    p1 = out_dir / "nere_to_admin_candidates.json"
    p2 = out_dir / "admin_to_ace_selected.template.json"
    p1.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    p2.write_text(json.dumps(admin_select, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "candidates": str(p1), "template": str(p2), "count": len(candidates['items'])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
