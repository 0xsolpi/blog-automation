#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re, html
from pathlib import Path
from datetime import datetime
import requests

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / '.env'
OUT = ROOT / 'data' / 'verified' / 'naver_resolved_products.json'


def load_env(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k,v=line.split('=',1)
        if k and k not in os.environ:
            os.environ[k]=v.strip()


def naver_shop_search(client_id: str, client_secret: str, query: str, display=20, start=1, sort='sim'):
    url='https://openapi.naver.com/v1/search/shop.json'
    headers={
        'X-Naver-Client-Id': client_id,
        'X-Naver-Client-Secret': client_secret,
    }
    params={'query':query,'display':display,'start':start,'sort':sort}
    r=requests.get(url,headers=headers,params=params,timeout=20)
    if r.status_code!=200:
        return []
    return r.json().get('items',[])


def strip_tags(s: str) -> str:
    return re.sub(r'<[^>]+>', '', html.unescape(s or '')).strip()


def extract_model(text: str) -> str:
    t=strip_tags(text)
    patterns=[
        r'\b[A-Z]{1,4}-?[A-Z0-9]{2,8}\b',
        r'\b[A-Z]{1,3}\d{2,5}[A-Z0-9+-]*\b',
        r'\b\d{2,4}[A-Z]{1,3}\b',
    ]
    for p in patterns:
        m=re.search(p,t)
        if m:
            cand=m.group(0)
            if len(cand)>=3:
                return cand
    return ''


def detect_brand(text: str) -> str:
    brands=['삼성','LG','애플','샤오미','다이슨','로보락','쿠쿠','쿠첸','브리타','필립스','테팔','라네즈','설화수','헤라','닥터지','뉴트리','정관장']
    t=strip_tags(text)
    for b in brands:
        if b in t:
            return b
    return ''


def pick_best(items: list[dict], query: str):
    scored=[]
    q_tokens=[x for x in re.split(r'\s+', query) if x]
    for it in items:
        title=strip_tags(it.get('title',''))
        brand=detect_brand(title)
        model=extract_model(title)
        lprice=int(it.get('lprice') or 0)
        score=0.0
        for qt in q_tokens:
            if qt in title:
                score += 1.2
        if brand:
            score += 1.0
        if model:
            score += 1.3
        if lprice>0:
            score += 0.4
        scored.append((score,{
            'canonical_product_name': title,
            'brand': brand,
            'model_name': model,
            'price': lprice,
            'mall_name': it.get('mallName',''),
            'product_link': it.get('link',''),
            'search_query': query,
            'match_confidence': round(min(0.98, 0.35 + score/8),2)
        }))
    scored.sort(key=lambda x:x[0], reverse=True)
    return scored[0][1] if scored else None


def main():
    load_env(ENV)
    cid=os.getenv('NAVER_CLIENT_ID','').strip()
    sec=os.getenv('NAVER_CLIENT_SECRET','').strip()
    if not cid or not sec:
        raise SystemExit('NAVER keys missing')

    ap=argparse.ArgumentParser()
    ap.add_argument('--queries', nargs='*', default=['로봇청소기','정수기','쿠션','프로틴','에어프라이어'])
    args=ap.parse_args()

    out=[]
    for q in args.queries:
        items=naver_shop_search(cid,sec,q,display=30,sort='sim')
        best=pick_best(items,q)
        if best:
            out.append(best)

    payload={
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'count': len(out),
        'items': out
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'ok':True,'count':len(out),'out':str(OUT)},ensure_ascii=False))

if __name__=='__main__':
    main()
