#!/usr/bin/env python3
import argparse
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "state" / "runs"
EVENT_DIR = ROOT / "events"


def now_iso():
    return datetime.now().astimezone().isoformat()


def load_state(path: Path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="run_id 상태/이벤트 기록 도구")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--from", dest="from_agent", default="unknown")
    ap.add_argument("--to", dest="to_agent", default="unknown")
    ap.add_argument("--status", default="in_progress")
    ap.add_argument("--retry-count", type=int, default=0)
    ap.add_argument("--meta", default="{}", help='JSON string')
    args = ap.parse_args()

    ts = now_iso()
    state_path = STATE_DIR / f"{args.run_id}.json"

    try:
        extra = json.loads(args.meta)
        if not isinstance(extra, dict):
            raise ValueError
    except Exception:
        raise SystemExit("--meta must be a valid JSON object string")

    prev = load_state(state_path) or {"run_id": args.run_id, "history": []}
    state = {
        "run_id": args.run_id,
        "stage": args.stage,
        "status": args.status,
        "from": args.from_agent,
        "to": args.to_agent,
        "retry_count": args.retry_count,
        "updated_at": ts,
        "meta": extra,
        "history": prev.get("history", []) + [{
            "stage": args.stage,
            "status": args.status,
            "from": args.from_agent,
            "to": args.to_agent,
            "retry_count": args.retry_count,
            "at": ts,
            "meta": extra,
        }]
    }
    save_json(state_path, state)

    event_name = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}_{args.stage}.json"
    event_path = EVENT_DIR / args.run_id / event_name
    save_json(event_path, {
        "run_id": args.run_id,
        "stage": args.stage,
        "status": args.status,
        "from": args.from_agent,
        "to": args.to_agent,
        "retry_count": args.retry_count,
        "generated_at": ts,
        "meta": extra,
    })

    print(f"state={state_path}")
    print(f"event={event_path}")


if __name__ == "__main__":
    main()
