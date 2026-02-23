#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re, html
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict
import requests

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / '.env'
OUT = ROOT / 'data' / 'trends' / 'luffy_output.json'

SHOP_CATEGORIES = [
    '로봇청소기','정수기','무선이어폰','노트북','에어프라이어','커피머신',
    '쿠션','선크림','앰플','프로틴','비타민','유산균'
]

BRANDS = ['삼성','LG','애플','샤오미','다이슨','로보락','쿠쿠','쿠첸','브리타','필립스','헤라','라네즈','설화수','닥터지']

NEWS_QUERIES = [
    '모델명', '출시', '품절', '리뷰', '화제', '인기', '내돈내산'
]

YT_QUERIES = [
    '내돈내산', '리뷰', '추천', '언박싱', '하울', '핫템'
]

NOISE = {'뉴스','속보','정치','대선','국회','정부','일보','신문','기자','공개','발표'}
MODEL_STOP = {'BESPOKE','CUCKOO','SAMSUNG','LG','APPLE','XIAOMI','DYSON','ROBOROCK'}



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


def strip_tags(s: str) -> str:
    return re.sub(r'<[^>]+>', '', html.unescape(s or '')).strip()


def normalize(s: str) -> str:
    s=strip_tags(s)
    s=re.sub(r'[^0-9A-Za-z가-힣\s\-\+]', ' ', s)
    s=re.sub(r'\s+', ' ', s).strip()
    return s


def detect_brand(text: str) -> str:
    t=normalize(text)
    for b in BRANDS:
        if b in t:
            return b
    return ''


def extract_model(text: str) -> str:
    t=normalize(text)
    patterns=[
        r'\b[A-Z]{1,4}\-?[A-Z0-9]{2,8}\b',
        r'\b[A-Z]{1,3}\d{2,5}[A-Z0-9\-\+]*\b',
        r'\b\d{2,4}[A-Z]{1,3}\b'
    ]
    for p in patterns:
        m=re.search(p,t)
        if m:
            x=m.group(0)
            if len(x)>=3 and x.lower() not in {'news','live'}:
                return x
    return ''


def entity_key(brand: str, model: str) -> str:
    return f"{brand}|{model}" if brand and model else ''


def normalize_model(model: str, brand: str) -> str:
    m = (model or '').strip().upper()
    b = (brand or '').strip().upper()
    if not m:
        return ''
    if m in MODEL_STOP:
        return ''
    if m == b:
        return ''
    # pure alpha short tokens are often line labels, not models
    if re.fullmatch(r'[A-Z]{2,6}', m):
        return ''
    # too generic words
    if m in {'PRO','MAX','ULTRA','AIR'}:
        return ''
    return m


def model_quality(model: str) -> float:
    if not model:
        return 0.0
    has_alpha = any(c.isalpha() for c in model)
    has_digit = any(c.isdigit() for c in model)
    if has_alpha and has_digit:
        return 0.9
    if has_digit and len(model) >= 4:
        return 0.6
    return 0.3


def naver_shop(cid, sec, q):
    r=requests.get('https://openapi.naver.com/v1/search/shop.json',headers={
        'X-Naver-Client-Id':cid,'X-Naver-Client-Secret':sec
    },params={'query':q,'display':20,'sort':'sim'},timeout=20)
    if r.status_code!=200:
        return []
    return r.json().get('items',[])


def naver_news(cid, sec, q):
    r=requests.get('https://openapi.naver.com/v1/search/news.json',headers={
        'X-Naver-Client-Id':cid,'X-Naver-Client-Secret':sec
    },params={'query':q,'display':10,'sort':'date'},timeout=20)
    if r.status_code!=200:
        return []
    return r.json().get('items',[])


def yt_search(key, q, hours=24):
    published_after=(datetime.now(timezone.utc)-timedelta(hours=hours)).isoformat().replace('+00:00','Z')
    r=requests.get('https://www.googleapis.com/youtube/v3/search',params={
        'part':'snippet','type':'video','q':q,'maxResults':15,'order':'date',
        'regionCode':'KR','relevanceLanguage':'ko','publishedAfter':published_after,'key':key
    },timeout=20)
    if r.status_code!=200:
        return []
    return r.json().get('items',[])


def valid_entity(brand, model):
    if not brand or not model:
        return False
    if any(n in brand for n in NOISE):
        return False
    if any(n in model for n in NOISE):
        return False
    if model.isdigit():
        return False
    if model in MODEL_STOP:
        return False
    if model == brand.upper():
        return False
    if model_quality(model) < 0.55:
        return False
    return True


def main():
    load_env(ENV)
    cid=os.getenv('NAVER_CLIENT_ID','').strip()
    sec=os.getenv('NAVER_CLIENT_SECRET','').strip()
    yk=os.getenv('YOUTUBE_API_KEY','').strip()

    ap=argparse.ArgumentParser()
    ap.add_argument('--hours',type=int,default=24)
    ap.add_argument('--top-n',type=int,default=20)
    args=ap.parse_args()

    if not cid or not sec:
        raise SystemExit('NAVER keys missing')

    pool=defaultdict(lambda:{
        'brand':'','model_name':'','canonical_product_name':'','mention_count_24h':0,
        'source_mix':defaultdict(int),'evidence_links':set(),'issue_reasons':[]
    })

    # 1) Naver shopping -> concrete entities seed
    for cat in SHOP_CATEGORIES:
        items=naver_shop(cid,sec,cat)
        for it in items[:10]:
            title=strip_tags(it.get('title',''))
            brand=detect_brand(title)
            model=normalize_model(extract_model(title), brand)
            if not valid_entity(brand,model):
                continue
            k=entity_key(brand,model)
            obj=pool[k]
            obj['brand']=brand; obj['model_name']=model; obj['canonical_product_name']=title
            obj['mention_count_24h'] += 2
            obj['source_mix']['naver_shop'] += 1
            link=it.get('link','')
            if link: obj['evidence_links'].add(link)
            obj['issue_reasons'].append(f'네이버 쇼핑 상위 노출: {cat}')

    # 2) Naver news mention enrichment by brand+model query
    keys=list(pool.keys())
    for k in keys:
        brand,model=k.split('|',1)
        q=f'{brand} {model}'
        news=naver_news(cid,sec,q)
        for n in news:
            t=strip_tags(n.get('title',''))
            if brand in t and model in normalize(t):
                obj=pool[k]
                obj['mention_count_24h'] += 1
                obj['source_mix']['naver_news'] += 1
                link=n.get('link') or n.get('originallink') or ''
                if link: obj['evidence_links'].add(link)
                obj['issue_reasons'].append('네이버 뉴스 24h 언급')

    # 3) YouTube mention enrichment (optional; skip on key/quota errors)
    if yk:
        for k in list(pool.keys())[:40]:
            brand,model=k.split('|',1)
            q=f'{brand} {model} 리뷰'
            vids=yt_search(yk,q,args.hours)
            if isinstance(vids,list):
                for v in vids:
                    sn=v.get('snippet',{})
                    title=sn.get('title','')
                    if brand in title and model in normalize(title):
                        obj=pool[k]
                        obj['mention_count_24h'] += 1
                        obj['source_mix']['youtube'] += 1
                        vid=(v.get('id',{}) or {}).get('videoId','')
                        if vid:
                            obj['evidence_links'].add(f'https://www.youtube.com/watch?v={vid}')
                            obj['issue_reasons'].append('유튜브 24h 리뷰/언급')

    # 4) scoring & output
    items=[]
    for k,obj in pool.items():
        if obj['mention_count_24h'] < 2:
            continue
        score=min(100, 45 + obj['mention_count_24h']*7 + len(obj['source_mix'])*5 + model_quality(obj['model_name'])*8)
        reasons=list(dict.fromkeys(obj['issue_reasons']))[:4]
        items.append({
            'entity_key':k,
            'brand':obj['brand'],
            'model_name':obj['model_name'],
            'canonical_product_name':obj['canonical_product_name'],
            'mention_count_24h':obj['mention_count_24h'],
            'score':round(score,1),
            'issue_reason':' / '.join(reasons) if reasons else '24시간 내 다중 소스 언급',
            'evidence_links':list(obj['evidence_links'])[:6],
            'source_mix':dict(obj['source_mix'])
        })

    items=sorted(items,key=lambda x:(x['score'],x['mention_count_24h']),reverse=True)[:args.top_n]

    payload={
        'run_id':datetime.now().strftime('%Y%m%d-%H%M%S'),
        'agent':'luffy',
        'generated_at':datetime.now().isoformat(timespec='seconds'),
        'time_window_hours':args.hours,
        'sources':['naver_shop','naver_news','youtube'],
        'mode':'entity-first',
        'items':items
    }

    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'ok':True,'count':len(items),'out':str(OUT)},ensure_ascii=False))

if __name__=='__main__':
    main()
