#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]

STAGE_FILES = {
    "luffy_to_ace": "luffy_to_ace.json",
    "ace_to_nami": "ace_to_nami.json",
    "nami_to_zoro": "nami_to_zoro.json",
    "zoro_to_nere": "zoro_to_nere.json",
    "robin_to_nere": "robin_to_nere.json",
    "nere_to_admin_candidates": "nere_to_admin_candidates.json",
    "admin_to_ace_selected": "admin_to_ace_selected.json",
    "admin_to_ace_selected_template": "admin_to_ace_selected.template.json",
    "nere_admin_candidate": "nere_to_admin_candidate_report.md",
    "nere_admin_published": "nere_to_admin_published_report.md",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default=datetime.now().strftime("%Y%m%d-%H%M%S"))
    ap.add_argument("--stage", choices=list(STAGE_FILES.keys()))
    args = ap.parse_args()

    base = ROOT / "data" / "handoff" / args.run_id
    base.mkdir(parents=True, exist_ok=True)
    if args.stage:
        out = base / STAGE_FILES[args.stage]
        print(json.dumps({"ok": True, "run_id": args.run_id, "stage": args.stage, "path": str(out)}, ensure_ascii=False))
        return

    mapping = {k: str(base / v) for k, v in STAGE_FILES.items()}
    print(json.dumps({"ok": True, "run_id": args.run_id, "base": str(base), "paths": mapping}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
