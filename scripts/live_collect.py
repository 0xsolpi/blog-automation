#!/usr/bin/env python3
"""
루피 live 수집기 (멀티소스 버전)
- Google Trends RSS + Google News RSS
- YouTube Data API (지난 N시간 업로드 영상)
- Naver DataLab Search Trend (후보 키워드 점수 보정)

출력: data/trends/top_items.json
"""

from __future__ import annotations
import argparse
import json
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import requests
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "trends" / "top_items.json"
ENV_PATH = ROOT / ".env"
CATEGORY_RULES_PATH = ROOT / "configs" / "category_rules.json"

RSS_SOURCES = [
    "https://trends.google.com/trending/rss?geo=KR",
    "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko",
]

CLOTHING_BLOCKLIST = {
    "의류", "옷", "코트", "패딩", "니트", "셔츠", "바지", "치마", "원피스", "자켓", "점퍼", "신발", "스니커즈",
    "가디건", "후드", "맨투맨", "청바지", "슬랙스", "구두", "부츠", "샌들",
}

STOPWORDS = {
    "자취", "아직도", "좁은", "요즘", "이렇게", "미친", "보이면", "신비로운", "없어서", "밋밋한", "셰프가", "독서", "절윤", "장동혁", "국힘", "국민의힘", "quot",
    "오늘", "최근", "이슈", "화제", "공개", "출시", "논란", "영상", "사진", "방송", "네이버", "유튜브", "인스타그램",
    "대한", "관련", "기자", "뉴스", "속보", "단독", "있다", "없다", "정리", "후기", "추천", "구매", "가격", "비교",
    "내일", "이번", "실시간", "라이브", "공식", "발표", "현장", "인터뷰",
}

PERSON_OR_NOISE_HINTS = {
    "기자", "선수", "감독", "배우", "가수", "대통령", "장관", "국회", "총리", "날씨", "증시", "환율",
    "국힘", "국민의힘", "민주당", "조선일보", "속보", "정치", "대선", "여야"
}

PRODUCT_SUFFIXES = {"청소기","배터리","이어폰","헤드셋","키보드","마우스","모니터","선풍기","가습기","공기청정기","영양제","안마기","믹서기","커피머신","정수기","제습기","블랙박스","스피커","태블릿","노트북","스탠드","조명","매트","베개","칫솔","치약","샴푸","클렌저","세제","건조기","거치대","케이스","쿠커","프라이팬","냄비","에어프라이어","로봇청소기"}

PHRASE_NOISE = {"내돈내산", "추천", "후기", "리뷰", "살까", "비교", "정리", "사용기", "브이로그", "shorts", "쇼츠", "언박싱", "할인", "핫딜"}

BRAND_HINTS = {"삼성","LG","샤오미","다이슨","필립스","브리타","쿠쿠","쿠첸","로보락","애플","소니","보스","한경희","테팔","발뮤다","샤크","위닉스","코웨이","캐치웰","일렉트로룩스"}

PRODUCT_HINTS = {
    "청소기", "보조배터리", "이어폰", "헤드셋", "키보드", "마우스", "모니터", "선풍기", "가습기", "공기청정기",
    "비타민", "영양제", "안마기", "믹서기", "커피머신", "정수기", "제습기", "블랙박스", "스피커", "태블릿",
    "노트북", "스탠드", "조명", "매트", "베개", "칫솔", "치약", "샴푸", "클렌저", "세제", "건조기",
}


def load_category_rules(path: Path):
    if not path.exists():
        return {"categories": {}, "noise_words": []}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"categories": {}, "noise_words": []}


def detect_category(name: str, rules: Dict) -> str:
    categories = (rules or {}).get("categories", {})
    text = normalize_text(name)
    best = ("기타", 0)
    for cat, cfg in categories.items():
        score = 0
        for h in cfg.get("hints", []):
            if h in text:
                score += 2
        for b in cfg.get("brands", []):
            if b in text:
                score += 1
        if score > best[1]:
            best = (cat, score)
    return best[0]


def category_match_score(name: str, category: str, rules: Dict) -> float:
    cats=(rules or {}).get("categories", {})
    cfg=cats.get(category, {})
    hints=cfg.get("hints", [])
    brands=cfg.get("brands", [])
    text=normalize_text(name)
    score=0.0
    for h in hints:
        if h in text:
            score += 0.5
    for b in brands:
        if b in text:
            score += 0.4
    if any(text.endswith(suf) or suf in text for suf in PRODUCT_SUFFIXES):
        score += 0.5
    if any(h in text for h in PRODUCT_HINTS):
        score += 0.5
    return min(1.5, score)


def category_product_ok(name: str, category: str, rules: Dict) -> bool:
    cats=(rules or {}).get("categories", {})
    cfg=cats.get(category, {})
    hints=cfg.get("hints", [])
    brands=cfg.get("brands", [])
    text=normalize_text(name)
    if category == "기타":
        return any(h in text for h in PRODUCT_HINTS) or any(text.endswith(suf) or suf in text for suf in PRODUCT_SUFFIXES)
    return any(h in text for h in hints) or any(b in text for b in brands)


def extract_category_entity_candidates(title: str, name: str, rules: Dict) -> List[Dict]:
    category = detect_category(f"{title} {name}", rules)
    base = build_entity_candidates(title, name)
    out=[]
    for c in base:
        c=dict(c)
        c["category"] = category
        cms = category_match_score(c.get("product_name",""), category, rules)
        if cms > 0:
            c["confidence"] = round(min(0.95, c.get("confidence",0.5)+min(0.2, cms*0.15)),2)
        out.append(c)
    return out


def load_env(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k and k not in os.environ:
            os.environ[k] = v.strip()


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_pubdate_to_utc(pub_date: str):
    if not pub_date:
        return None
    fmts = ["%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"]
    for f in fmts:
        try:
            dt = datetime.strptime(pub_date, f)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            continue
    return None


def normalize_text(s: str) -> str:
    s = re.sub(r"\[[^\]]+\]", " ", s)
    s = re.sub(r"\([^\)]+\)", " ", s)
    s = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def token_candidates(text: str) -> List[str]:
    toks = [t for t in normalize_text(text).split() if 2 <= len(t) <= 16]
    out = []
    for t in toks:
        if t in STOPWORDS or t in CLOTHING_BLOCKLIST:
            continue
        if t.lower() in {"tv", "th", "vs", "kr", "ko"}:
            continue
        out.append(t)
    return out


def is_clothing(name: str) -> bool:
    return any(k in name for k in CLOTHING_BLOCKLIST)


def clean_item_name(name: str) -> str:
    x = normalize_text(name)
    parts = []
    for t in x.split():
        if t.lower() in {"shorts", "vlog", "review", "best"}:
            continue
        if t in PHRASE_NOISE:
            continue
        if t.isdigit() or re.fullmatch(r"\d+[년월일시분]?", t):
            continue
        parts.append(t)
    if not parts:
        return ""
    # 2-gram까지 허용
    if len(parts) >= 2:
        cand = f"{parts[0]} {parts[1]}"
    else:
        cand = parts[0]
    cand = cand.strip()
    if len(cand) > 22:
        cand = cand[:22].strip()
    return cand


def is_probable_product(name: str) -> bool:
    n = normalize_text(name)
    if not n:
        return False
    if any(noise in n for noise in PERSON_OR_NOISE_HINTS):
        return False
    if n in STOPWORDS:
        return False
    if re.fullmatch(r"\d+[년월일시분]?", n):
        return False
    if any(h in n for h in PRODUCT_HINTS):
        return True
    if any(n.endswith(suf) or suf in n for suf in PRODUCT_SUFFIXES):
        return True
    # 2-gram 중 하나라도 제품 힌트가 있으면 허용
    toks=n.split()
    return any(any(h in t for h in PRODUCT_HINTS) for t in toks)


def product_likelihood(name: str) -> float:
    score = 0.0
    if any(h in name for h in PRODUCT_HINTS):
        score += 0.7
    if any(h in name for h in PERSON_OR_NOISE_HINTS):
        score -= 0.5
    if re.fullmatch(r"[A-Za-z]{1,2}", name or ""):
        score -= 0.7
    if len(name) <= 1:
        score -= 0.8
    return score


def fetch_rss(url: str, timeout: int = 15) -> List[Dict]:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    root = ET.fromstring(r.text)
    out = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        if title and link:
            out.append({"title": title, "link": link, "pubDate": pub_date, "source": "rss"})
    return out


def filter_recent_rows(rows: List[Dict], hours=24) -> List[Dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out = []
    for r in rows:
        dt = parse_pubdate_to_utc(r.get("pubDate", ""))
        if dt is None:
            continue
        if dt >= cutoff:
            out.append(r)
    return out


def extract_seed_keywords(rows: List[Dict], max_k=40) -> List[str]:
    c = Counter()
    for r in rows:
        for t in token_candidates(r.get("title", "")):
            c[t] += 1
    keys = [k for k, _ in c.most_common(max_k)]
    return [k for k in keys if not is_clothing(k)]


def fetch_youtube_rows(api_key: str, hours: int, seed_keywords: List[str], per_query=15) -> List[Dict]:
    base = "https://www.googleapis.com/youtube/v3/search"
    published_after = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat().replace("+00:00", "Z")

    default_queries = [
        "쿠팡 추천템",
        "생활용품 추천",
        "자취 필수템",
        "가전 추천",
        "주방템 추천",
        "차량용품 추천",
        "헬스케어 기기 추천",
        "수납 정리템",
        "스마트 기기 추천",
        "육아 필수템",
    ]
    queries = default_queries + seed_keywords[:4] + ["쿠팡", "인기 제품", "추천 아이템"]
    rows = []
    for q in queries:
        params = {
            "part": "snippet",
            "type": "video",
            "maxResults": per_query,
            "q": q,
            "order": "viewCount",
            "regionCode": "KR",
            "relevanceLanguage": "ko",
            "publishedAfter": published_after,
            "key": api_key,
        }
        r = requests.get(base, params=params, timeout=20)
        if r.status_code != 200:
            continue
        data = r.json()
        for it in data.get("items", []):
            sn = it.get("snippet", {})
            title = (sn.get("title") or "").strip()
            vid = (it.get("id", {}) or {}).get("videoId", "")
            if not title or not vid:
                continue
            rows.append(
                {
                    "title": title,
                    "link": f"https://www.youtube.com/watch?v={vid}",
                    "pubDate": sn.get("publishedAt", ""),
                    "source": "youtube",
                }
            )
        time.sleep(0.15)
    return rows


def fetch_youtube_rows_recent_date(api_key: str, hours: int, queries: List[str], per_query=10) -> List[Dict]:
    base = "https://www.googleapis.com/youtube/v3/search"
    published_after = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat().replace("+00:00", "Z")
    rows=[]
    for q in queries[:8]:
        params = {
            "part": "snippet",
            "type": "video",
            "maxResults": per_query,
            "q": q,
            "order": "date",
            "regionCode": "KR",
            "relevanceLanguage": "ko",
            "publishedAfter": published_after,
            "key": api_key,
        }
        r = requests.get(base, params=params, timeout=20)
        if r.status_code != 200:
            continue
        data = r.json()
        for it in data.get("items", []):
            sn = it.get("snippet", {})
            vid = (it.get("id", {}) or {}).get("videoId", "")
            title = (sn.get("title") or "").strip()
            if title and vid:
                rows.append({"title": title, "link": f"https://www.youtube.com/watch?v={vid}", "pubDate": sn.get("publishedAt", ""), "source": "youtube"})
        time.sleep(0.1)
    return rows


def parse_iso_to_utc(s: str):
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def filter_recent_iso_rows(rows: List[Dict], hours=24) -> List[Dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out = []
    for r in rows:
        dt = parse_iso_to_utc(r.get("pubDate", ""))
        if dt and dt >= cutoff:
            out.append(r)
    return out




def fetch_youtube_with_fallbacks(api_key: str, hours: int, seed_keywords: List[str], target_rows: int = 260) -> List[Dict]:
    rows = fetch_youtube_rows(api_key, hours, seed_keywords, per_query=15)
    if len(rows) >= target_rows:
        return rows

    extra_queries = [
        "로봇청소기 추천", "무선 이어폰 추천", "가성비 태블릿", "차량용 블랙박스", "주방 가전 추천",
        "캠핑 용품 추천", "헬스 보충제 추천", "수납용품 추천", "공기청정기 추천", "가습기 추천"
    ]
    rows2 = []
    for q in extra_queries:
        rows2.extend(fetch_youtube_rows(api_key, hours, [q], per_query=10))
        if len(rows) + len(rows2) >= target_rows:
            break
    return rows + rows2

def datalab_scores(client_id: str, client_secret: str, keywords: List[str]) -> Dict[str, float]:
    """
    DataLab Search Trend는 키워드 그룹 추이 API라 '발굴'보다 '보정'에 사용.
    후보 키워드를 그룹으로 넣고 최근 일자 ratio를 받아 가중치로 반영.
    """
    if not keywords:
        return {}

    end = datetime.now().date()
    start = end - timedelta(days=7)

    groups = []
    for k in keywords[:20]:
        groups.append({"groupName": k, "keywords": [k]})

    payload = {
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "timeUnit": "date",
        "keywordGroups": groups,
        "device": "",
        "ages": [],
        "gender": "",
    }
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json",
    }

    url = "https://openapi.naver.com/v1/datalab/search"
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
    if r.status_code != 200:
        return {}

    data = r.json()
    out = {}
    for row in data.get("results", []):
        kw = row.get("title", "")
        points = row.get("data", [])
        if not kw or not points:
            continue
        ratio = points[-1].get("ratio", 0.0) or 0.0
        out[kw] = float(ratio)
    return out


def extract_model_tokens(text: str) -> List[str]:
    t = normalize_text(text)
    parts = t.split()
    models = []
    for p in parts:
        # ex) V12, S8, Q5, WH1000XM5, M7, A9, 9800, X2
        if re.fullmatch(r"[A-Za-z]{1,4}\d{1,5}[A-Za-z0-9-]*", p):
            models.append(p)
            continue
        # ex) Q5+ / S8Pro / XM5-like already normalized may remove +
        if re.fullmatch(r"[A-Za-z0-9-]{3,}", p) and any(ch.isdigit() for ch in p) and any(ch.isalpha() for ch in p):
            models.append(p)
    # dedupe preserve order
    out=[]
    for m in models:
        if m not in out:
            out.append(m)
    return out[:3]


def detect_brand(text: str) -> str:
    t = normalize_text(text)
    for b in BRAND_HINTS:
        if b in t:
            return b
    return ""


def build_entity_candidates(title: str, name: str) -> List[Dict]:
    brand = detect_brand(title)
    models = extract_model_tokens(title)
    cands = []

    if brand and models:
        for m in models[:2]:
            cands.append({
                "brand": brand,
                "model": m,
                "product_name": f"{brand} {name}".strip(),
                "confidence": 0.85,
            })
    elif brand:
        cands.append({
            "brand": brand,
            "model": "",
            "product_name": f"{brand} {name}".strip(),
            "confidence": 0.7,
        })
    elif models:
        for m in models[:2]:
            cands.append({
                "brand": "",
                "model": m,
                "product_name": name,
                "confidence": 0.65,
            })

    if not cands:
        cands.append({
            "brand": "",
            "model": "",
            "product_name": name,
            "confidence": 0.5,
        })
    return cands


def choose_item_name(title: str) -> Optional[str]:
    raw = normalize_text(title)
    toks = token_candidates(title)
    if not toks:
        return None

    # 1) 제품 힌트가 포함된 복합어 우선 추출
    for hint in PRODUCT_HINTS:
        if hint in raw:
            # hint 주변 토큰을 찾아 1~2gram으로 반환
            parts = raw.split()
            for i, t in enumerate(parts):
                if hint in t:
                    if i > 0 and len(parts[i-1]) <= 8:
                        cand = (parts[i-1] + " " + t).strip()
                        if not is_clothing(cand):
                            return cand
                    return t

    # 2) suffix 기반 후보(예: xxx청소기, xxx배터리)
    parts = raw.split()
    for i,t in enumerate(parts):
        if any(t.endswith(suf) or suf in t for suf in PRODUCT_SUFFIXES):
            if i>0 and len(parts[i-1])<=8:
                cand=(parts[i-1]+" "+t).strip()
                if not is_clothing(cand):
                    return cand
            return t

    # 3) 단일 토큰 fallback은 '제품성 높은 토큰'만 허용
    for t in toks:
        if is_clothing(t):
            continue
        if t.isdigit() or re.fullmatch(r"\d+[년월일시분]?", t):
            continue
        if any(n in t for n in PERSON_OR_NOISE_HINTS):
            continue
        if any(h in t for h in PRODUCT_HINTS):
            return clean_item_name(t)

    return None


def build_items(rows: List[Dict], top_n: int, source_weight: Dict[str, float], naver_weight: Dict[str, float], category_rules: Dict) -> List[Dict]:
    counts = Counter()
    links = defaultdict(list)
    titles = defaultdict(list)
    src_counts = defaultdict(Counter)

    for r in rows:
        name = choose_item_name(r.get("title", ""))
        if not name:
            continue
        name = clean_item_name(name)
        if not name:
            continue
        if is_clothing(name):
            continue
        if name.isdigit() or re.fullmatch(r"\d+[년월일시분]?", name):
            continue
        if any(n in name for n in PERSON_OR_NOISE_HINTS):
            continue
        if len(name) < 2:
            continue
        cat_guess = detect_category(name, category_rules)
        cm = category_match_score(name, cat_guess, category_rules)
        if not is_probable_product(name) and cm < 0.5:
            continue

        w = source_weight.get(r.get("source", "rss"), 1.0) + (cm * 0.15)
        counts[name] += w
        if r.get("link") and r["link"] not in links[name]:
            links[name].append(r["link"])
        if r.get("title"):
            titles[name].append(r["title"])
        src_counts[name][r.get("source", "rss")] += 1

    items = []
    for name, c in counts.most_common(200):
        pl = product_likelihood(name)
        if pl < -0.3:
            continue

        n_ratio = naver_weight.get(name, 0.0)
        score = 48 + c * 10 + n_ratio * 0.25 + pl * 12
        score = max(0, min(100, round(score, 1)))

        reason = f"최근 {24}시간 내 멀티소스 언급 증가"
        top_title = titles[name][0] if titles.get(name) else ""
        if top_title:
            reason += f" (예: {top_title[:50]})"

        source_mix = dict(src_counts[name])
        src_text = ", ".join(f"{k}:{v}" for k, v in source_mix.items())
        if src_text:
            reason += f" / 소스분포[{src_text}]"

        entities = extract_category_entity_candidates(top_title or name, name, category_rules)

        items.append(
            {
                "item_name": name,
                "trend_topic": name,
                "issue_reason": reason,
                "evidence_links": links[name][:5],
                "score": score,
                "observed_at": now_iso(),
                "source": "multi(rss,youtube,naver_datalab)",
                "source_mix": source_mix,
                "naver_ratio": round(n_ratio, 2),
                "product_likelihood": round(pl, 2),
                "category": (entities[0].get("category") if entities else "기타"),
                "entity_candidates": entities,
            }
        )

    return items[:top_n]


def coarse_fallback_items(rows: List[Dict], top_n: int) -> List[Dict]:
    c = Counter()
    links = defaultdict(list)
    for r in rows:
        for t in token_candidates(r.get("title", "")):
            if t in STOPWORDS or is_clothing(t):
                continue
            if t.isdigit():
                continue
            c[t]+=1
            if r.get("link") and r["link"] not in links[t]:
                links[t].append(r["link"])
    out=[]
    for name,n in c.most_common(top_n*3):
        if len(name)<2:
            continue
        out.append({
            "item_name": name,
            "trend_topic": name,
            "issue_reason": "최근 24시간 RSS 기반 보강 후보",
            "evidence_links": links[name][:3],
            "score": max(40, min(65, 40+n*3)),
            "observed_at": now_iso(),
            "source": "fallback-rss",
            "source_mix": {"rss": n},
            "naver_ratio": 0.0,
            "product_likelihood": 0.0,
            "category": detect_category(name, {"categories": {}}),
            "entity_candidates": [{"brand":"","model":"","product_name":name,"confidence":0.4,"category":"기타"}],
        })
        if len(out)>=top_n:
            break
    return out


def main():
    load_env(ENV_PATH)
    category_rules = load_category_rules(CATEGORY_RULES_PATH)

    ap = argparse.ArgumentParser()
    ap.add_argument("--top-n", type=int, default=20)
    ap.add_argument("--hours", type=int, default=24)
    args = ap.parse_args()

    yt_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    naver_id = os.getenv("NAVER_CLIENT_ID", "").strip()
    naver_secret = os.getenv("NAVER_CLIENT_SECRET", "").strip()

    errors = []
    dynamic_noise = set((category_rules or {}).get("noise_words", []))
    if dynamic_noise:
        STOPWORDS.update(dynamic_noise)

    # 1) RSS
    rss_raw = []
    for src in RSS_SOURCES:
        try:
            rss_raw.extend(fetch_rss(src))
            time.sleep(0.2)
        except Exception as e:
            errors.append({"source": src, "error": str(e)})
    rss_recent = filter_recent_rows(rss_raw, hours=args.hours)

    # 2) Seed keywords from RSS
    seeds = extract_seed_keywords(rss_recent, max_k=40)

    # 3) YouTube
    yt_recent = []
    if yt_key:
        try:
            yt_rows = fetch_youtube_with_fallbacks(yt_key, hours=args.hours, seed_keywords=seeds, target_rows=260)
            yt_recent = filter_recent_iso_rows(yt_rows, hours=args.hours)
            if len(yt_recent) == 0:
                yt_rows2 = fetch_youtube_rows_recent_date(yt_key, hours=args.hours, queries=seeds[:8] or ["쿠팡", "추천템", "핫템"], per_query=12)
                yt_recent = filter_recent_iso_rows(yt_rows2, hours=args.hours)
        except Exception as e:
            errors.append({"source": "youtube", "error": str(e)})

    # 4) Merge rows and build preliminary keywords for naver weighting
    merged_rows = rss_recent + yt_recent
    if not merged_rows and rss_recent:
        merged_rows = rss_recent
    if not merged_rows:
        raise SystemExit(f"수집 실패: 최근 {args.hours}시간 데이터 없음. errors={errors}")

    prelim_keywords = extract_seed_keywords(merged_rows, max_k=30)

    # 5) Naver DataLab (weighting)
    naver_scores = {}
    if naver_id and naver_secret:
        try:
            naver_scores = datalab_scores(naver_id, naver_secret, prelim_keywords)
        except Exception as e:
            errors.append({"source": "naver_datalab", "error": str(e)})

    # 6) Final build
    source_weight = {"rss": 1.0, "youtube": 1.2}
    items = build_items(merged_rows, top_n=args.top_n, source_weight=source_weight, naver_weight=naver_scores, category_rules=category_rules)

    if len(items) < args.top_n:
        # 약한 필터로 2차 보강(개수 확보)
        refill_rows = []
        for r in merged_rows:
            title = r.get("title", "")
            cands = token_candidates(title)
            for t in cands[:2]:
                t2 = clean_item_name(t)
                if not t2 or is_clothing(t2):
                    continue
                if t2.isdigit() or re.fullmatch(r"\d+[년월일시분]?", t2):
                    continue
                if not is_probable_product(t2):
                    continue
                refill_rows.append({"title": t2, "link": r.get("link", ""), "source": r.get("source", "rss")})

        extra = build_items(refill_rows, top_n=args.top_n * 2, source_weight=source_weight, naver_weight=naver_scores, category_rules=category_rules)
        existing = {x["item_name"] for x in items}
        for e in extra:
            if e["item_name"] in existing:
                continue
            items.append(e)
            existing.add(e["item_name"])
            if len(items) >= args.top_n:
                break

    if len(items) == 0:
        items = coarse_fallback_items(rss_recent or merged_rows, top_n=args.top_n)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "count": len(items),
        "hours": args.hours,
        "out": str(OUT),
        "rss_raw": len(rss_raw),
        "rss_recent": len(rss_recent),
        "youtube_recent": len(yt_recent),
        "seed_count": len(seeds),
        "naver_weight_count": len(naver_scores),
        "errors": errors[:5],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
