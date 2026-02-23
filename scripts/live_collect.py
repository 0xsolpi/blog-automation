#!/usr/bin/env python3
"""
루피 live 수집기 (초기 버전)
- Google Trends RSS(KR) + Google News RSS(KR) 기반으로 최근 이슈 아이템 후보 추출
- 의류 키워드 제외
- 점수(score) 부여 후 상위 N개 저장
출력: data/trends/top_items.json
"""

from __future__ import annotations
import argparse
import json
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import requests
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "trends" / "top_items.json"

CLOTHING_BLOCKLIST = {
    "의류", "옷", "코트", "패딩", "니트", "셔츠", "바지", "치마", "원피스", "자켓", "점퍼", "신발", "스니커즈"
}

STOPWORDS = {
    "오늘", "최근", "이슈", "화제", "공개", "출시", "논란", "영상", "사진", "방송", "네이버", "유튜브", "인스타그램",
    "대한", "관련", "기자", "뉴스", "속보", "단독", "있다", "없다", "정리", "후기", "추천", "구매", "가격", "비교"
}

RSS_SOURCES = [
    "https://trends.google.com/trending/rss?geo=KR",
    "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
]


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def fetch_rss(url: str, timeout: int = 15) -> List[Dict]:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    root = ET.fromstring(r.text)
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "pubDate": pub_date})
    return items


def normalize_text(s: str) -> str:
    s = re.sub(r"\[[^\]]+\]", " ", s)
    s = re.sub(r"\([^\)]+\)", " ", s)
    s = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def candidate_tokens(title: str) -> List[str]:
    t = normalize_text(title)
    toks = [x for x in t.split() if len(x) >= 2]
    filtered = []
    for tok in toks:
        if tok in STOPWORDS:
            continue
        if tok in CLOTHING_BLOCKLIST:
            continue
        filtered.append(tok)
    return filtered


def likely_item_name(title: str) -> str:
    toks = candidate_tokens(title)
    if not toks:
        return title[:40]
    # 단순 휴리스틱: 길이 2~8 토큰 중 앞쪽 우선
    for tok in toks:
        if 2 <= len(tok) <= 12:
            return tok
    return toks[0]


def is_clothing(item_name: str) -> bool:
    return any(k in item_name for k in CLOTHING_BLOCKLIST)


def build_items(raw_rows: List[Dict], top_n: int) -> List[Dict]:
    names = [likely_item_name(r["title"]) for r in raw_rows]
    cnt = Counter(names)

    grouped_links: Dict[str, List[str]] = {}
    grouped_titles: Dict[str, List[str]] = {}
    for r, n in zip(raw_rows, names):
        grouped_links.setdefault(n, [])
        grouped_titles.setdefault(n, [])
        if r["link"] not in grouped_links[n]:
            grouped_links[n].append(r["link"])
        grouped_titles[n].append(r["title"])

    items = []
    for name, c in cnt.most_common():
        if is_clothing(name):
            continue
        links = grouped_links.get(name, [])[:5]
        titles = grouped_titles.get(name, [])[:3]
        score = min(100, 55 + c * 9)
        reason = f"최근 기사/트렌드 피드에서 '{name}' 키워드 언급 빈도 증가"
        if titles:
            reason += f" (예: {titles[0][:50]})"

        items.append(
            {
                "item_name": name,
                "issue_reason": reason,
                "evidence_links": links,
                "score": score,
                "observed_at": now_iso(),
                "source": "google-rss",
            }
        )

    return items[:top_n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=20)
    args = ap.parse_args()

    raw = []
    errors = []
    for src in RSS_SOURCES:
        try:
            rows = fetch_rss(src)
            raw.extend(rows)
            time.sleep(0.3)
        except Exception as e:
            errors.append({"source": src, "error": str(e)})

    if not raw:
        raise SystemExit(f"수집 실패: usable RSS 없음. errors={errors}")

    items = build_items(raw, args.top_n)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"ok": True, "count": len(items), "out": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
