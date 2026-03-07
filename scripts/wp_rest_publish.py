#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import mimetypes
from pathlib import Path

import requests


def upload_media(site: str, user: str, app_pw: str, file_path: Path):
    if not file_path.exists():
        raise FileNotFoundError(f"missing media: {file_path}")
    if not file_path.is_file():
        raise ValueError(f"not a file: {file_path}")
    if file_path.stat().st_size <= 0:
        raise ValueError(f"empty media file: {file_path}")

    url = f"{site.rstrip('/')}/wp-json/wp/v2/media"
    ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    headers = {
        "Content-Disposition": f'attachment; filename="{file_path.name}"',
    }

    # Use multipart upload so file binding is explicit and stable.
    with file_path.open("rb") as f:
        files = {"file": (file_path.name, f, ctype)}
        r = requests.post(url, headers=headers, files=files, auth=(user, app_pw), timeout=60)

    r.raise_for_status()
    j = r.json()
    return {
        "id": j["id"],
        "source_url": j["source_url"],
        "slug": j.get("slug"),
        "local_path": str(file_path),
        "bytes": file_path.stat().st_size,
    }


def publish_post(site: str, user: str, app_pw: str, title: str, content_html: str, status: str = "publish", featured_media: int | None = None):
    url = f"{site.rstrip('/')}/wp-json/wp/v2/posts"
    payload = {"title": title, "content": content_html, "status": status}
    if featured_media:
        payload["featured_media"] = featured_media
    r = requests.post(url, json=payload, auth=(user, app_pw), timeout=60)
    r.raise_for_status()
    j = r.json()
    return {"id": j["id"], "link": j.get("link"), "status": j.get("status")}


def main():
    ap = argparse.ArgumentParser(description="WP REST media upload + post publish helper")
    ap.add_argument("--site", required=True)
    ap.add_argument("--user", required=True)
    ap.add_argument("--app-password", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--html-file", required=True)
    ap.add_argument("--media", nargs="*", default=[])
    ap.add_argument("--status", default="publish")
    args = ap.parse_args()

    html = Path(args.html_file).read_text(encoding="utf-8")

    uploaded = []
    for m in args.media:
        p = Path(m).expanduser().resolve()
        uploaded.append(upload_media(args.site, args.user, args.app_password, p))

    featured = uploaded[0]["id"] if uploaded else None
    post = publish_post(args.site, args.user, args.app_password, args.title, html, args.status, featured)

    print(json.dumps({"ok": True, "uploaded": uploaded, "post": post}, ensure_ascii=False))


if __name__ == "__main__":
    main()
