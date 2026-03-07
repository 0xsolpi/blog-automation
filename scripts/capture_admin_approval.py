#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def main() -> None:
    ap = argparse.ArgumentParser(description="Persist admin publish approval for a run_id")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--approver", default="admin")
    ap.add_argument("--source", default="telegram")
    ap.add_argument("--message-id", default="")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    run_id = args.run_id.strip()
    if not run_id:
        raise SystemExit("run_id is required")

    handoff_dir = ROOT / "data" / "handoff" / run_id
    handoff_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "run_id": run_id,
        "from": "admin",
        "to": "nere",
        "generated_at": now_iso(),
        "approval": {
            "type": "publish",
            "status": "approved",
            "approver": args.approver,
            "source": args.source,
            "message_id": args.message_id,
            "note": args.note,
        },
    }

    approval_path = handoff_dir / "admin_publish_approval.json"
    approval_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # state/event append
    import subprocess

    meta_obj = {
        "approval_file": str(approval_path.relative_to(ROOT)),
        "source": args.source,
        "message_id": args.message_id,
    }
    proc = subprocess.run(
        [
            "python3",
            str(ROOT / "scripts" / "run_state.py"),
            "--run-id", run_id,
            "--stage", "ADMIN_APPROVED",
            "--from", "admin",
            "--to", "robin",
            "--status", "done",
            "--meta", json.dumps(meta_obj, ensure_ascii=False),
        ],
        cwd=ROOT,
    )
    if proc.returncode != 0:
        raise SystemExit("approval file saved, but state/event logging failed")

    print(json.dumps({
        "ok": True,
        "run_id": run_id,
        "approval_file": str(approval_path.relative_to(ROOT)),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
