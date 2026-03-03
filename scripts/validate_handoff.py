#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path

REQUIRED_META = ["run_id", "from", "to", "generated_at"]

SCHEMA = {
    "luffy_to_ace": {
        "array_key": "items",
        "required_item": [
            "rank", "product_name", "issue_reason", "evidence_links",
            "search_metrics", "trend_strength", "conversion_potential", "risk_level"
        ],
    },
    "ace_to_nami": {
        "array_key": "validated_items",
        "required_item": [
            "rank", "product_name", "coupang_link", "final_profitability_score", "risk_level"
        ],
    },
    "nami_to_zoro": {
        "array_key": "drafts",
        "required_item": [
            "rank", "title", "markdown_path", "product_name", "coupang_link", "risk_level",
            "category", "tags", "image_manifest"
        ],
    },
    "zoro_to_nere": {
        "array_key": "reviews",
        "required_item": ["title", "result", "risk_level", "notes"],
    },
    "robin_to_nere": {
        "array_key": "published",
        "required_item": ["title", "post_id", "post_url", "published_at", "status"],
    },
}


def is_missing(v):
    return v is None or (isinstance(v, str) and v.strip() == "")


PLACEHOLDER_RE = re.compile(r"\{\{WP_IMAGE_[A-Z0-9_]+\}\}")


def _load_content(item: dict, base_dir: Path) -> str:
    inline = item.get("content_markdown")
    if isinstance(inline, str) and inline.strip():
        return inline
    md_path = item.get("markdown_path")
    if isinstance(md_path, str) and md_path.strip():
        p = Path(md_path)
        if not p.is_absolute():
            p = (base_dir / p).resolve()
        if p.exists():
            return p.read_text(encoding="utf-8")
    return ""


def _validate_nami_item(item: dict, i: int, errs: list[str], base_dir: Path):
    tags = item.get("tags")
    if not isinstance(tags, list) or len(tags) == 0:
        errs.append(f"drafts[{i}] tags must be non-empty array")

    manifest = item.get("image_manifest")
    if not isinstance(manifest, dict):
        errs.append(f"drafts[{i}] image_manifest must be object")
        return

    featured = manifest.get("featured_image")
    body_images = manifest.get("body_images")
    placeholder_map = manifest.get("placeholder_to_file")

    if is_missing(featured):
        errs.append(f"drafts[{i}] image_manifest.featured_image missing")
    if not isinstance(body_images, list):
        errs.append(f"drafts[{i}] image_manifest.body_images must be array")
        body_images = []
    if not isinstance(placeholder_map, dict):
        errs.append(f"drafts[{i}] image_manifest.placeholder_to_file must be object")
        placeholder_map = {}

    all_files = []
    if isinstance(featured, str) and featured.strip():
        all_files.append(featured.strip())
    all_files.extend([x.strip() for x in body_images if isinstance(x, str) and x.strip()])
    all_files.extend([v.strip() for v in placeholder_map.values() if isinstance(v, str) and v.strip()])

    if len(all_files) != len(set(all_files)):
        errs.append(f"drafts[{i}] image filenames must be unique (duplicate detected)")

    for ph in placeholder_map.keys():
        if not isinstance(ph, str) or not PLACEHOLDER_RE.fullmatch(ph):
            errs.append(f"drafts[{i}] invalid placeholder key: {ph}")

    content = _load_content(item, base_dir)
    placeholders_in_content = set(PLACEHOLDER_RE.findall(content))
    if placeholders_in_content:
        missing = [ph for ph in sorted(placeholders_in_content) if ph not in placeholder_map]
        if missing:
            errs.append(f"drafts[{i}] missing placeholder mapping: {', '.join(missing)}")


def validate(payload: dict, stage: str, base_dir: Path) -> list[str]:
    errs: list[str] = []
    for k in REQUIRED_META:
        if is_missing(payload.get(k)):
            errs.append(f"missing meta: {k}")

    conf = SCHEMA[stage]
    arr_key = conf["array_key"]
    arr = payload.get(arr_key)
    if not isinstance(arr, list):
        errs.append(f"{arr_key} must be array")
        return errs

    for i, item in enumerate(arr):
        if not isinstance(item, dict):
            errs.append(f"{arr_key}[{i}] must be object")
            continue
        for req in conf["required_item"]:
            if is_missing(item.get(req)):
                errs.append(f"{arr_key}[{i}] missing: {req}")
        if stage == "nami_to_zoro":
            _validate_nami_item(item, i, errs, base_dir)
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=list(SCHEMA.keys()), required=True)
    ap.add_argument("--input", required=True)
    args = ap.parse_args()

    input_path = Path(args.input)
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    errs = validate(payload, args.stage, input_path.parent)
    out = {"ok": len(errs) == 0, "stage": args.stage, "errors": errs}
    print(json.dumps(out, ensure_ascii=False))
    raise SystemExit(0 if out["ok"] else 2)


if __name__ == "__main__":
    main()
