#!/usr/bin/env python3
"""Backfill zoro DONE decisions from session transcripts into workspace state/handoff files.

Why:
- In unstable relay/ACK situations, PASS/FIX/HOLD can exist only in chat history,
  while `state/runs/<run_id>.json` and `data/handoff/<run_id>/zoro_to_nere.json` are missing.
- This script reconciles that gap so nere gate and daily checks see consistent state.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "state" / "runs"
HANDOFF_DIR = ROOT / "data" / "handoff"
EVENT_DIR = ROOT / "events"

TRANSCRIPT_GLOB = Path.home() / ".openclaw" / "agents" / "zoro" / "sessions"

RUN_RE = re.compile(r"run_id\s*=\s*([0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{4}-[a-z0-9-]+)", re.I)
VERDICT_RE = re.compile(r"\b(PASS|FIX|HOLD)\b", re.I)
DONE_HINT_RE = re.compile(r"ZORO_DONE|최종 판정|final_decision", re.I)


@dataclass
class Decision:
    run_id: str
    verdict: str
    generated_at: str
    transcript: Path


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def parse_line(line: str, transcript: Path) -> Optional[Decision]:
    try:
        obj = json.loads(line)
    except Exception:
        return None

    if obj.get("type") != "message":
        return None

    msg = obj.get("message") or {}
    if msg.get("role") != "assistant":
        return None

    contents = msg.get("content") or []
    texts = []
    for c in contents:
        if isinstance(c, dict) and c.get("type") == "text":
            t = c.get("text")
            if isinstance(t, str):
                texts.append(t)
    if not texts:
        return None

    text_blob = "\n".join(texts)
    if not DONE_HINT_RE.search(text_blob):
        return None

    run_m = RUN_RE.search(text_blob)
    if not run_m:
        return None

    ver_m = VERDICT_RE.search(text_blob)
    if not ver_m:
        return None

    ts = (msg.get("timestamp") or obj.get("timestamp") or now_iso())
    return Decision(
        run_id=run_m.group(1),
        verdict=ver_m.group(1).upper(),
        generated_at=ts,
        transcript=transcript,
    )


def latest_decisions() -> dict[str, Decision]:
    found: dict[str, Decision] = {}
    for p in sorted(TRANSCRIPT_GLOB.glob("*.jsonl"), key=lambda x: x.stat().st_mtime):
        try:
            with p.open("r", encoding="utf-8") as f:
                for line in f:
                    d = parse_line(line, p)
                    if d:
                        found[d.run_id] = d
        except Exception:
            continue
    return found


def write_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def backfill(decision: Decision, dry_run: bool) -> list[str]:
    changes = []
    run_id = decision.run_id
    state_path = STATE_DIR / f"{run_id}.json"
    handoff_path = HANDOFF_DIR / run_id / "zoro_to_nere.json"

    if not state_path.exists():
        stage = f"ZORO_{decision.verdict}"
        state = {
            "run_id": run_id,
            "stage": stage,
            "status": "done",
            "from": "zoro",
            "to": "nere",
            "retry_count": 0,
            "updated_at": now_iso(),
            "meta": {
                "reconciled": True,
                "source": "zoro_session_transcript",
                "transcript": str(decision.transcript),
                "verdict": decision.verdict,
                "message_generated_at": decision.generated_at,
            },
            "history": [
                {
                    "stage": stage,
                    "status": "done",
                    "from": "zoro",
                    "to": "nere",
                    "retry_count": 0,
                    "at": now_iso(),
                    "meta": {
                        "reconciled": True,
                        "source": "zoro_session_transcript",
                        "transcript": str(decision.transcript),
                        "verdict": decision.verdict,
                        "message_generated_at": decision.generated_at,
                    },
                }
            ],
        }
        if not dry_run:
            write_json(state_path, state)
        changes.append(f"create state {state_path}")

        event_path = EVENT_DIR / run_id / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}_ZORO_{decision.verdict}.json"
        event = {
            "run_id": run_id,
            "stage": f"ZORO_{decision.verdict}",
            "status": "done",
            "from": "zoro",
            "to": "nere",
            "retry_count": 0,
            "generated_at": now_iso(),
            "meta": {
                "reconciled": True,
                "source": "zoro_session_transcript",
                "transcript": str(decision.transcript),
                "verdict": decision.verdict,
                "message_generated_at": decision.generated_at,
            },
        }
        if not dry_run:
            write_json(event_path, event)
        changes.append(f"create event {event_path}")

    if not handoff_path.exists():
        handoff = {
            "run_id": run_id,
            "from": "zoro",
            "to": "nere",
            "generated_at": now_iso(),
            "verdict": decision.verdict,
            "risk_level": "UNKNOWN",
            "notes": {
                "reconciled": True,
                "source": "zoro_session_transcript",
                "transcript": str(decision.transcript),
                "message_generated_at": decision.generated_at,
            },
        }
        if not dry_run:
            write_json(handoff_path, handoff)
        changes.append(f"create handoff {handoff_path}")

    return changes


def main():
    ap = argparse.ArgumentParser(description="Reconcile missing zoro->nere handoff/state from session logs")
    ap.add_argument("--run-id", help="Only reconcile this run_id")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    decisions = latest_decisions()
    if args.run_id:
        decisions = {k: v for k, v in decisions.items() if k == args.run_id}

    if not decisions:
        print("no zoro DONE decisions found")
        return

    total_changes = 0
    for run_id in sorted(decisions.keys()):
        d = decisions[run_id]
        changes = backfill(d, dry_run=args.dry_run)
        if changes:
            print(f"[{run_id}] verdict={d.verdict}")
            for c in changes:
                print(" -", c)
            total_changes += len(changes)

    if total_changes == 0:
        print("already consistent: no missing files")


if __name__ == "__main__":
    main()
