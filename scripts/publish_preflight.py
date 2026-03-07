#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path

FORBIDDEN_LINK_PATTERNS = [
    r"\]\(\.{2}/",
    r"\]\([^)]*\.md\)",
    r"\]\(https?://your-domain\.com[^)]*\)",
]
PLACEHOLDER_PATTERN = re.compile(r"\{\{WP_IMAGE_[^}]+\}\}")
RELATIVE_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(\./images/[^)]+\)")
RAW_MARKDOWN_PATTERN = re.compile(r"(^|\n)#{1,6}\s|!\[[^\]]*\]\([^\)]+\)|\[[^\]]+\]\([^\)]+\)", re.M)


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

    rel_imgs = RELATIVE_IMAGE_PATTERN.findall(text)
    if rel_imgs:
        issues.append({"type": "relative_image_path", "count": len(rel_imgs)})

    raw_md_hits = RAW_MARKDOWN_PATTERN.findall(text)
    if raw_md_hits:
        issues.append({"type": "raw_markdown_exposed", "count": len(raw_md_hits)})

    return {
        "file": str(path),
        "ok": len(issues) == 0,
        "issues": issues,
    }


def check_manifest(path: Path):
    issues = []
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"file": str(path), "ok": False, "issues": [{"type": "invalid_manifest_json", "error": str(e)}]}

    imgs = obj.get("images") or []
    if not isinstance(imgs, list) or not imgs:
        issues.append({"type": "manifest_images_empty"})
        return {"file": str(path), "ok": False, "issues": issues}

    for i, im in enumerate(imgs, start=1):
        lp = (im or {}).get("local_path")
        if not lp:
            issues.append({"type": "missing_local_path", "index": i})
            continue
        p = Path(lp)
        candidates = []
        if p.is_absolute():
            candidates = [p]
        else:
            # support both manifest-relative and workspace-relative paths
            candidates = [
                (path.parent / p).resolve(),
                (Path.cwd() / p).resolve(),
            ]

        resolved = None
        for c in candidates:
            if c.exists():
                resolved = c
                break

        if resolved is None:
            issues.append({"type": "missing_image_file", "index": i, "local_path": str(candidates[0])})
            continue

        p = resolved
        if not p.is_file():
            issues.append({"type": "image_not_file", "index": i, "local_path": str(p)})
            continue
        if p.stat().st_size <= 0:
            issues.append({"type": "image_empty", "index": i, "local_path": str(p)})

    return {"file": str(path), "ok": len(issues) == 0, "issues": issues}


def main():
    ap = argparse.ArgumentParser(description="Preflight checks before WP publish")
    ap.add_argument("--files", nargs="+", default=[])
    ap.add_argument("--manifests", nargs="*", default=[])
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    if not args.files and not args.manifests:
        raise SystemExit("at least one of --files or --manifests is required")

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

    for m in args.manifests:
        p = Path(m)
        if not p.exists():
            item = {"file": m, "ok": False, "issues": [{"type": "missing_manifest"}]}
        else:
            item = check_manifest(p)
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
