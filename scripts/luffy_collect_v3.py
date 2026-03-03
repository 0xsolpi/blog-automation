#!/usr/bin/env python3
from __future__ import annotations
import os, re, json, argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
import requests

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / '.env'
OUT = ROOT / 'data' / 'trends' / 'luffy_v3_candidates.json'

CELEBS = ['아이유','장원영','카리나','안유진','한소희','박보영','유재석','기안84','덱스','제니','지수','로제','정국','차은우','임영웅','이효리','화사','선미','박은빈','김지원','사쿠라','윈터']
PRODUCTS = ['쿠션','선크림','립','앰플','향수','가방','신발','로봇청소기','정수기','이어폰','노트북','틴트','파운데이션','립밤']
SNS_HINTS = ['인스타','릴스','쇼츠','틱톡','SNS','바이럴','화제','품절','추천템']
BROADCAST_HINTS = ['방송','예능','드라마','홈쇼핑','PPL','협찬','사용템','왓츠인마이백']
BRANDS = ['디올','샤넬','헤라','라네즈','설화수','닥터지','삼성','LG','애플','로보락','조선미녀','구찌','프라다','SK-Ⅱ','SK-II','마몽드']
NOISE = ['정치','대선','국정연설','코스피','증시','ETF','야구','축구','운세']


def load_env(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        if k and k not in os.environ:
            os.environ[k] = v.strip()


def clean(s: str) -> str:
    s = re.sub(r'<[^>]+>', ' ', s or '')
    s = s.replace('&quot;', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def is_recent_news(pub: str, hours: int) -> bool:
    if not pub:
        return False
    for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z']:
        try:
            dt = datetime.strptime(pub, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt >= datetime.now(timezone.utc) - timedelta(hours=hours)
        except Exception:
            pass
    return False


def is_recent_blog(postdate: str, hours: int) -> bool:
    if not re.fullmatch(r'\d{8}', postdate or ''):
        return False
    dt = datetime.strptime(postdate, '%Y%m%d').replace(tzinfo=timezone.utc)
    return dt >= datetime.now(timezone.utc) - timedelta(hours=hours)


def naver(api: str, cid: str, sec: str, q: str, display=8):
    url = f'https://openapi.naver.com/v1/search/{api}.json'
    r = requests.get(url, headers={'X-Naver-Client-Id': cid, 'X-Naver-Client-Secret': sec}, params={'query': q, 'display': display, 'sort': 'date'}, timeout=20)
    if r.status_code != 200:
        return []
    return r.json().get('items', [])


def youtube(yk: str, q: str, hours: int, max_results=8):
    url = 'https://www.googleapis.com/youtube/v3/search'
    after = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat().replace('+00:00', 'Z')
    r = requests.get(url, params={
        'part': 'snippet', 'q': q, 'type': 'video', 'maxResults': max_results,
        'order': 'date', 'regionCode': 'KR', 'relevanceLanguage': 'ko',
        'publishedAfter': after, 'key': yk
    }, timeout=20)
    if r.status_code != 200:
        return []
    return r.json().get('items', [])


def detect_product_name(text: str) -> str:
    toks = text.split()
    for i, t in enumerate(toks):
        if any(p in t for p in PRODUCTS):
            left = toks[i-1] if i > 0 else ''
            return (left + ' ' + t).strip()
    return ''


def detect_brand(text: str) -> str:
    for b in BRANDS:
        if b in text:
            return b
    return ''


def score(text: str, source: str, bucket: str, brand: str, product: str) -> int:
    s = 0
    if any(c in text for c in CELEBS): s += 2
    if any(h in text for h in SNS_HINTS): s += 2
    if any(h in text for h in BROADCAST_HINTS): s += 2
    if brand: s += 2
    if product: s += 2
    if bucket == 'SNS급상승': s += 1
    if source == 'youtube': s += 1
    return s


def confidence(sc: int) -> str:
    if sc >= 8: return '상'
    if sc >= 6: return '중'
    return '하'


def title_has_celeb_and_product_or_brand(title: str) -> bool:
    t = title or ''
    has_celeb = any(c in t for c in CELEBS)
    has_prod_or_brand = any(p in t for p in PRODUCTS) or any(b in t for b in BRANDS)
    return has_celeb and has_prod_or_brand


def main():
    load_env(ENV)
    cid = os.getenv('NAVER_CLIENT_ID', '').strip()
    sec = os.getenv('NAVER_CLIENT_SECRET', '').strip()
    yk = os.getenv('YOUTUBE_API_KEY', '').strip()
    if not cid or not sec:
        raise SystemExit('NAVER keys missing')

    ap = argparse.ArgumentParser()
    ap.add_argument('--hours', type=int, default=24)
    ap.add_argument('--limit', type=int, default=80)
    args = ap.parse_args()

    rows = []

    # 1) SNS 급상승 제품
    sns_queries = [
        f'{c} {p} 인스타' for c in CELEBS[:10] for p in PRODUCTS[:8]
    ] + [
        f'{p} 릴스 화제' for p in PRODUCTS[:8]
    ]

    for q in sns_queries[:120]:
        for it in naver('news', cid, sec, q, 6):
            if not is_recent_news(it.get('pubDate', ''), args.hours):
                continue
            t = clean(it.get('title', '')); d = clean(it.get('description', '')); txt = f'{t} {d}'
            if any(n in txt for n in NOISE):
                continue
            if not (any(h in txt for h in SNS_HINTS) and any(p in txt for p in PRODUCTS)):
                continue
            product = detect_product_name(txt); brand = detect_brand(txt)
            title_priority = title_has_celeb_and_product_or_brand(t)
            if not title_priority and (not product and not brand):
                continue
            sc = score(txt, 'naver_news', 'SNS급상승', brand, product) + (2 if title_priority else 0)
            rows.append({'bucket': 'SNS급상승', 'source': 'naver_news', 'title': t, 'link': it.get('link', ''), 'product_name': product, 'brand': brand, 'title_priority': title_priority, 'score': sc, 'confidence': confidence(sc)})

        for it in naver('blog', cid, sec, q, 6):
            if not is_recent_blog(it.get('postdate', ''), args.hours):
                continue
            t = clean(it.get('title', '')); d = clean(it.get('description', '')); txt = f'{t} {d}'
            if any(n in txt for n in NOISE):
                continue
            if not (any(h in txt for h in SNS_HINTS) and any(p in txt for p in PRODUCTS)):
                continue
            product = detect_product_name(txt); brand = detect_brand(txt)
            title_priority = title_has_celeb_and_product_or_brand(t)
            if not title_priority and (not product and not brand):
                continue
            sc = score(txt, 'naver_blog', 'SNS급상승', brand, product) + (2 if title_priority else 0)
            rows.append({'bucket': 'SNS급상승', 'source': 'naver_blog', 'title': t, 'link': it.get('link', ''), 'product_name': product, 'brand': brand, 'title_priority': title_priority, 'score': sc, 'confidence': confidence(sc)})

    if yk:
        for q in [f'{c} 추천템 쇼츠' for c in CELEBS[:8]] + [f'{p} 쇼츠 추천' for p in PRODUCTS[:6]]:
            for it in youtube(yk, q, args.hours, 6):
                sn = it.get('snippet', {})
                vid = (it.get('id', {}) or {}).get('videoId', '')
                if not vid:
                    continue
                t = clean(sn.get('title', '')); d = clean(sn.get('description', '')); txt = f'{t} {d}'
                if any(n in txt for n in NOISE):
                    continue
                if not any(p in txt for p in PRODUCTS):
                    continue
                product = detect_product_name(txt); brand = detect_brand(txt)
                title_priority = title_has_celeb_and_product_or_brand(t)
                if not title_priority and (not product and not brand):
                    continue
                sc = score(txt, 'youtube', 'SNS급상승', brand, product) + (2 if title_priority else 0)
                rows.append({'bucket': 'SNS급상승', 'source': 'youtube', 'title': t, 'link': f'https://www.youtube.com/watch?v={vid}', 'product_name': product, 'brand': brand, 'title_priority': title_priority, 'score': sc, 'confidence': confidence(sc)})

    # 2) 뉴스/방송 + 연예인 연관 제품
    rel_queries = [f'{c} {p} 방송' for c in CELEBS[:10] for p in PRODUCTS[:8]] + [f'예능 {p}' for p in PRODUCTS[:8]]
    for q in rel_queries[:120]:
        for it in naver('news', cid, sec, q, 6):
            if not is_recent_news(it.get('pubDate', ''), args.hours):
                continue
            t = clean(it.get('title', '')); d = clean(it.get('description', '')); txt = f'{t} {d}'
            if any(n in txt for n in NOISE):
                continue
            if not ((any(c in txt for c in CELEBS) or any(b in txt for b in BROADCAST_HINTS)) and any(p in txt for p in PRODUCTS)):
                continue
            product = detect_product_name(txt); brand = detect_brand(txt)
            title_priority = title_has_celeb_and_product_or_brand(t)
            if not title_priority and (not product and not brand):
                continue
            sc = score(txt, 'naver_news', '뉴스/방송연예', brand, product) + (2 if title_priority else 0)
            rows.append({'bucket': '뉴스/방송연예', 'source': 'naver_news', 'title': t, 'link': it.get('link', ''), 'product_name': product, 'brand': brand, 'title_priority': title_priority, 'score': sc, 'confidence': confidence(sc)})

    # dedupe + sort
    uniq = []
    seen = set()
    for r in rows:
        k = (r['title'], r['link'])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)

    uniq.sort(key=lambda x: (x.get('title_priority', False), x['score']), reverse=True)
    uniq = uniq[:args.limit]

    out = {
        'run_id': datetime.now().strftime('%Y%m%d-%H%M%S'),
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'time_window_hours': args.hours,
        'criteria': ['24h', 'SNS 급상승 제품', '뉴스/방송 연예인 연관 제품'],
        'count': len(uniq),
        'counts': {
            'SNS급상승': sum(1 for x in uniq if x['bucket'] == 'SNS급상승'),
            '뉴스/방송연예': sum(1 for x in uniq if x['bucket'] == '뉴스/방송연예'),
            '상': sum(1 for x in uniq if x['confidence'] == '상'),
            '중': sum(1 for x in uniq if x['confidence'] == '중'),
            '하': sum(1 for x in uniq if x['confidence'] == '하'),
            'title_priority': sum(1 for x in uniq if x.get('title_priority')),
        },
        'items': uniq
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'ok': True, 'out': str(OUT), 'count': len(uniq), 'counts': out['counts']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
