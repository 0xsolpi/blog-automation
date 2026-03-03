#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import time
import fcntl
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
INP = ROOT / "data" / "handoff" / "nere_to_ace.json"
OUT = ROOT / "data" / "verified" / "verified_items.json"

DOMAIN = "https://api-gateway.coupang.com"
PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/products/search"
DEEPLINK_PATH = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"

# 호출 안전장치: 1분에 45회 초과 금지 (요청한 정책)
# 중요: 프로세스 단위가 아니라 "전체 실행" 기준으로 제한
MAX_CALLS_PER_MINUTE = 45
_CALL_TIMES = deque()  # same-process fallback
RATE_FILE = Path('/tmp/coupang_rate_limit.json')


def _throttle_shared_rate_limit():
    RATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with RATE_FILE.open('a+', encoding='utf-8') as f:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.seek(0)
        raw = f.read().strip()
        try:
            arr = json.loads(raw) if raw else []
        except Exception:
            arr = []

        now = time.time()
        arr = [ts for ts in arr if isinstance(ts, (int, float)) and now - ts < 60]

        if len(arr) >= MAX_CALLS_PER_MINUTE:
            sleep_for = 60 - (now - arr[0]) + 0.05
            if sleep_for > 0:
                time.sleep(sleep_for)
            now = time.time()
            arr = [ts for ts in arr if now - ts < 60]

        arr.append(now)
        f.seek(0)
        f.truncate(0)
        f.write(json.dumps(arr))
        f.flush()
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def throttle_coupang_calls():
    # 1) 전체 프로세스 공유 제한
    _throttle_shared_rate_limit()

    # 2) 동일 프로세스 내 보조 제한(방어)
    now = time.time()
    while _CALL_TIMES and now - _CALL_TIMES[0] >= 60:
        _CALL_TIMES.popleft()
    if len(_CALL_TIMES) >= MAX_CALLS_PER_MINUTE:
        sleep_for = 60 - (now - _CALL_TIMES[0]) + 0.05
        if sleep_for > 0:
            time.sleep(sleep_for)
    _CALL_TIMES.append(time.time())


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def rfc_zulu() -> str:
    return datetime.now(timezone.utc).strftime("%y%m%dT%H%M%SZ")


def build_auth(access_key: str, secret_key: str, method: str, path: str, query: str, dt: str) -> str:
    # Coupang signature rule: signed-date + method + path + query (without '?')
    msg = f"{dt}{method}{path}{query}"
    sig = hmac.new(secret_key.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={dt}, signature={sig}"


def search_coupang(access_key: str, secret_key: str, keyword: str, limit: int = 10) -> list[dict[str, Any]]:
    query = f"keyword={quote(keyword)}&limit={limit}"
    path_with_query = f"{PATH}?{query}"
    dt = rfc_zulu()
    headers = {
        "Authorization": build_auth(access_key, secret_key, "GET", PATH, query, dt),
        "Content-Type": "application/json",
    }
    url = DOMAIN + path_with_query
    throttle_coupang_calls()
    r = requests.get(url, headers=headers, timeout=25)
    r.raise_for_status()
    body = r.json()
    if body.get("rCode") != "0":
        raise RuntimeError(f"coupang_api_error: {body.get('rMessage')} ({body.get('rCode')})")
    data = body.get("data", {}) or {}
    return data.get("productData", []) or []


def to_deeplink(access_key: str, secret_key: str, urls: list[str]) -> dict[str, str]:
    # returns {original_url: tracking_url}
    if not urls:
        return {}
    dt = rfc_zulu()
    headers = {
        "Authorization": build_auth(access_key, secret_key, "POST", DEEPLINK_PATH, "", dt),
        "Content-Type": "application/json",
    }
    payload = {"coupangUrls": urls}
    throttle_coupang_calls()
    r = requests.post(DOMAIN + DEEPLINK_PATH, headers=headers, json=payload, timeout=25)
    r.raise_for_status()
    body = r.json()
    if body.get("rCode") != "0":
        raise RuntimeError(f"coupang_deeplink_error: {body.get('rMessage')} ({body.get('rCode')})")
    data = body.get("data", []) or []
    out = {}
    for row in data:
        original = row.get("originalUrl", "")
        short = row.get("shortenUrl", "") or row.get("landingUrl", "")
        if original and short:
            out[original] = short
    return out


def normalize(text: str) -> str:
    return "".join((text or "").lower().split())


def score_match(item: dict[str, Any], product: dict[str, Any]) -> float:
    title = (product.get("productName") or "")
    ntitle = normalize(title)
    brand = normalize(item.get("brand", ""))
    model = normalize(item.get("model_name", ""))
    canonical = normalize(item.get("canonical_product_name", ""))

    score = 0.0
    if brand and brand in ntitle:
        score += 0.35
    if model and model in ntitle:
        score += 0.45

    # canonical overlap (rough)
    if canonical:
        common = 0
        for tok in canonical.split():
            if tok and tok in ntitle:
                common += 1
        if common >= 2:
            score += min(0.2, common * 0.03)

    return min(0.99, score)


def pick_by_business_rules(candidates: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    meta = {
        "selection_basis": "",
        "rocket_selected_by_1pct_rule": False,
        "price_delta_ratio": None,
    }
    if not candidates:
        return None, meta

    # 1) 최저가 우선
    priced = [c for c in candidates if isinstance(c.get("productPrice"), (int, float))]
    if not priced:
        meta["selection_basis"] = "fallback_first_candidate"
        return candidates[0], meta

    priced.sort(key=lambda x: float(x.get("productPrice", 0)))
    cheapest = priced[0]
    cheapest_price = float(cheapest.get("productPrice", 0))

    # 4) 일반배송 vs 로켓배송 가격차 1% 이내면 로켓배송 선택
    rockets = [c for c in priced if bool(c.get("isRocket"))]
    if cheapest_price > 0 and rockets:
        rocket_best = min(rockets, key=lambda x: float(x.get("productPrice", 0)))
        rocket_price = float(rocket_best.get("productPrice", 0))
        ratio = (rocket_price - cheapest_price) / cheapest_price
        meta["price_delta_ratio"] = ratio
        if ratio <= 0.01:
            meta["selection_basis"] = "rocket_within_1pct_of_cheapest"
            meta["rocket_selected_by_1pct_rule"] = True
            return rocket_best, meta

    meta["selection_basis"] = "cheapest_price"
    return cheapest, meta


def best_match(item: dict[str, Any], candidates: list[dict[str, Any]], min_confidence: float) -> tuple[dict[str, Any] | None, float, str | None, dict[str, Any]]:
    scored: list[tuple[dict[str, Any], float]] = []
    for c in candidates:
        s = score_match(item, c)
        if s >= min_confidence:
            scored.append((c, s))

    if not scored:
        return None, 0.0, "low_confidence_or_no_match", {}

    # 2,3) 리뷰수/평점 제약은 응답 필드 존재 시에만 적용
    with_review = []
    for c, s in scored:
        rc = c.get("reviewCount")
        rt = c.get("rating")
        if rc is None and rt is None:
            with_review.append((c, s))
            continue
        try:
            rc_ok = int(rc or 0) >= 10
            rt_ok = float(rt or 0) > 3.0
        except Exception:
            rc_ok = False
            rt_ok = False
        if rc_ok and rt_ok:
            with_review.append((c, s))

    if not with_review:
        return None, 0.0, "review_constraints_not_met_or_unavailable", {}

    chosen, rule_meta = pick_by_business_rules([c for c, _ in with_review])
    if not chosen:
        return None, 0.0, "no_candidate_after_rules", {}

    conf = 0.0
    for c, s in with_review:
        if c is chosen:
            conf = s
            break
    return chosen, conf, None, rule_meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(INP))
    ap.add_argument("--output", default=str(OUT))
    ap.add_argument("--min-confidence", type=float, default=0.65)
    args = ap.parse_args()

    access_key = os.getenv("COUPANG_ACCESS_KEY", "").strip()
    secret_key = os.getenv("COUPANG_SECRET_KEY", "").strip()
    if not access_key or not secret_key:
        raise SystemExit("missing COUPANG_ACCESS_KEY/COUPANG_SECRET_KEY in .env")

    src = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out: list[dict[str, Any]] = []
    deeplink_cache: dict[str, str] = {}

    for it in src.get("items", []):
        queries = it.get("search_queries_seed", []) or []
        if not queries:
            queries = [f"{it.get('brand','')} {it.get('model_name','')}", it.get("canonical_product_name", "")]

        searched: list[str] = []
        merged: list[dict[str, Any]] = []
        err: str | None = None
        for q in queries[:3]:
            q = (q or "").strip()
            if not q:
                continue
            searched.append(q)
            try:
                merged.extend(search_coupang(access_key, secret_key, q, limit=8))
            except Exception as e:
                err = str(e)

        common = {
            "entity_key": it.get("entity_key", ""),
            "trend_topic": it.get("trend_topic", ""),
            "canonical_product_name": it.get("canonical_product_name", ""),
            "brand": it.get("brand", ""),
            "model_name": it.get("model_name", ""),
            "mention_count_24h": it.get("mention_count_24h", 0),
            "score": it.get("score", 0),
            "selection_reason": it.get("selection_reason", {}),
            "issue_reason": it.get("issue_reason", ""),
            "evidence_links": it.get("evidence_links", []),
            "evidence_briefs": it.get("evidence_briefs", []),
            "source_mix": it.get("source_mix", {}),
            "precheck_confidence": it.get("precheck_confidence", 0),
        }

        if not merged:
            out.append({
                **common,
                "coupang_available": False,
                "match_confidence": 0.0,
                "search_queries_tried": searched,
                "rejection_reason": err or "no_search_result",
                "checked_at": now_iso(),
            })
            continue

        chosen, conf, rej, rule_meta = best_match(it, merged, args.min_confidence)
        if not chosen:
            out.append({
                **common,
                "coupang_available": False,
                "match_confidence": round(conf, 2),
                "search_queries_tried": searched,
                "rejection_reason": rej or "low_confidence_or_no_match",
                "checked_at": now_iso(),
            })
            continue

        product_url = chosen.get("productUrl", "")
        partner_url = ""
        try:
            if product_url in deeplink_cache:
                partner_url = deeplink_cache[product_url]
            elif product_url:
                m = to_deeplink(access_key, secret_key, [product_url])
                partner_url = m.get(product_url, "")
                if partner_url:
                    deeplink_cache[product_url] = partner_url
        except Exception:
            partner_url = ""

        review_count = chosen.get("reviewCount")
        rating = chosen.get("rating")

        nami_use_notes = []
        if isinstance(review_count, (int, float)) and isinstance(rating, (int, float)):
            if int(review_count) >= 1000 and float(rating) >= 4.5:
                nami_use_notes.append(
                    f"상품평 {int(review_count)}개 이상, 평점 {float(rating):.1f}점으로 구매자 만족도가 높은 상품"
                )

        if rule_meta.get("rocket_selected_by_1pct_rule"):
            ratio = rule_meta.get("price_delta_ratio")
            pct = f"{(ratio or 0)*100:.2f}%"
            nami_use_notes.append(
                f"일반배송 최저가 대비 가격차 {pct}로 1% 이내여서 로켓배송 상품을 선택"
            )

        out.append({
            **common,
            "matched_product_title": chosen.get("productName", ""),
            "coupang_available": True,
            "coupang_partner_url": partner_url or product_url,
            "match_confidence": round(conf, 2),
            "search_queries_tried": searched,
            "selected_price": chosen.get("productPrice"),
            "is_rocket": bool(chosen.get("isRocket")),
            "review_count": review_count,
            "rating": rating,
            "selection_basis": rule_meta.get("selection_basis"),
            "price_delta_ratio_vs_cheapest": rule_meta.get("price_delta_ratio"),
            "nami_use_notes": nami_use_notes,
            "top_reviews": [],
            "review_image_urls": [],
            "top_reviews_note": "쿠팡 파트너스 검색 API 응답에 리뷰 본문/이미지 필드가 없어 현재 미수집",
            "rule_notes": [
                "lowest_price_preferred",
                "exclude_rating_le_3_when_available",
                "exclude_review_lt_10_when_available",
                "rocket_preferred_if_within_1pct",
            ],
            "checked_at": now_iso(),
        })

    output = {
        "run_id": src.get("run_id", ""),
        "from": "ace",
        "to": "nami",
        "generated_at": now_iso(),
        "items": out,
    }

    op = Path(args.output)
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    ok = sum(1 for x in out if x.get("coupang_available"))
    print(json.dumps({"ok": True, "total": len(out), "verified": ok, "out": str(op)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
