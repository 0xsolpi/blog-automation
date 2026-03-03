#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

FORBIDDEN_LINK_PATTERNS = [r"\]\(\.{2}/", r"\]\([^)]*\.md\)"]
PLACEHOLDER_PATTERN = re.compile(r"\{\{WP_IMAGE_[^}]+\}\}")


def check_file(path: Path):
    text = path.read_text(encoding="utf-8")
    issues = []

    placeholders = PLACEHOLDER_PATTERN.findall(text)
    if placeholders:
        issues.append({"type": "placeholder_remaining", "count": len(placeholders)})

    for pat in FORBIDDEN_LINK_PATTERNS:
        found = re.findall(pat, text)
        if found:
            issues.append({"type": "forbidden_internal_link", "pattern": pat, "count": len(found)})

    return {
        "file": str(path),
        "ok": len(issues) == 0,
        "issues": issues,
    }


def main():
    ap = argparse.ArgumentParser(description="Preflight checks before WP publish")
    ap.add_argument("--files", nargs="+", required=True)
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    results = []
    all_ok = True
    for f in args.files:
        p = Path(f)
        if not p.exists():
            item = {"file": f, "ok": False, "issues": [{"type": "missing_file"}]}
        else:
            item = check_file(p)
        all_ok = all_ok and item["ok"]
        results.append(item)

    report = {"ok": all_ok, "results": results}

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False))
    raise SystemExit(0 if all_ok else 2)


if __name__ == "__main__":
    main()
