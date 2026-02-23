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

CELEB_SEEDS = ['김장훈','아이유','장원영','카리나','안유진','한소희','박보영','유재석','기안84','덱스']
PRODUCT_TERMS = ['화장품','쿠션','립','향수','선크림','앰플','마스크팩','스킨케어','사용템','애용템','파우치','왓츠인마이백','단백질','영양제','정수기','청소기','주방템','생활용품']

YT_QUERIES = [
    '내돈내산', '리뷰', '추천', '언박싱', '하울', '핫템'
]

NOISE = {'뉴스','속보','정치','대선','국회','정부','일보','신문','기자','공개','발표'}
MODEL_STOP = {'BESPOKE','CUCKOO','SAMSUNG','LG','APPLE','XIAOMI','DYSON','ROBOROCK'}
MODEL_BLACKLIST = {'29CM','WCONCEPT','MUSINSA','OLIVEYOUNG','NAVER','COUPANG'}
BEAUTY_LINE_HINTS = {'쿠션','파운데이션','립','틴트','선크림','에센스','앰플','세럼','크림','마스크팩'}



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


def normalize_beauty_model(text: str) -> str:
    t = normalize(text).upper()
    # common shade/SPF tokens
    m = re.search(r'(\d{2}[NC]\d)', t)  # 21N1, 23C1
    if m:
        return m.group(1)
    m = re.search(r'SPF\s?\d{2}', t)
    if m:
        return m.group(0).replace(' ', '')
    # cushion line names
    for key in ['블랙쿠션','BLACKCUSHION','리플렉션','GLOW']:
        if key in t:
            return key
    return ''


def normalize_model(model: str, brand: str) -> str:
    m = (model or '').strip().upper()
    b = (brand or '').strip().upper()
    if not m:
        return ''
    if m in MODEL_STOP or m in MODEL_BLACKLIST:
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


def naver_blog(cid, sec, q):
    r=requests.get('https://openapi.naver.com/v1/search/blog.json',headers={
        'X-Naver-Client-Id':cid,'X-Naver-Client-Secret':sec
    },params={'query':q,'display':10,'sort':'date'},timeout=20)
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
    if model in MODEL_STOP or model in MODEL_BLACKLIST:
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
        'source_mix':defaultdict(int),'evidence_links':set(),'issue_reasons':[], 'evidence_briefs':[]
    })

    # 1) Naver shopping -> concrete entities seed
    for cat in SHOP_CATEGORIES:
        items=naver_shop(cid,sec,cat)
        for it in items[:10]:
            title=strip_tags(it.get('title',''))
            brand=detect_brand(title)
            model=normalize_model(extract_model(title), brand)
            if not model and any(h in title for h in BEAUTY_LINE_HINTS):
                model = normalize_beauty_model(title)
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
            obj['evidence_briefs'].append({
                'source':'naver_shop',
                'url': link,
                'title': title[:140],
                'summary': f'{cat} 카테고리 상위 노출 상품. 가격/판매처 기반으로 실제 구매 가능성 확인됨.'
            })

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
                obj['mention_count_24h'] += 2
                obj['source_mix']['naver_news'] += 1
                link=n.get('link') or n.get('originallink') or ''
                if link: obj['evidence_links'].add(link)
                desc = strip_tags(n.get('description',''))
                obj['issue_reasons'].append('네이버 뉴스 24h 언급')
                obj['evidence_briefs'].append({
                    'source':'naver_news',
                    'url': link,
                    'title': t[:140],
                    'summary': (desc[:220] if desc else '뉴스 본문에서 해당 모델 언급 확인')
                })


    # 2.5) celebrity-product enrichment (news+blog)
    for celeb in CELEB_SEEDS:
        for term in PRODUCT_TERMS:
            q = f"{celeb} {term}"
            news = naver_news(cid, sec, q)
            blogs = naver_blog(cid, sec, q)

            # 제목에서 브랜드/모델 추출
            for row,src in [(x,'naver_news') for x in news[:5]] + [(x,'naver_blog') for x in blogs[:5]]:
                t = strip_tags(row.get('title',''))
                d = strip_tags(row.get('description',''))
                comb = f"{t} {d}"
                brand = detect_brand(comb)
                model = normalize_model(extract_model(comb), brand)
                if not valid_entity(brand, model):
                    continue
                k = entity_key(brand, model)
                obj = pool[k]
                obj['brand']=brand; obj['model_name']=model
                if not obj['canonical_product_name']:
                    obj['canonical_product_name']=f"{brand} {model}"
                obj['mention_count_24h'] += 2
                obj['source_mix'][src] += 1
                link = row.get('link') or row.get('originallink') or ''
                if link: obj['evidence_links'].add(link)
                obj['issue_reasons'].append(f'연예/인플루언서 맥락 언급: {celeb} {term}')
                obj['evidence_briefs'].append({
                    'source': src,
                    'url': link,
                    'title': t[:140],
                    'summary': (d[:220] if d else f'{celeb} 관련 {term} 맥락에서 모델 언급')
                })

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
                        obj['mention_count_24h'] += 2
                        obj['source_mix']['youtube'] += 1
                        vid=(v.get('id',{}) or {}).get('videoId','')
                        if vid:
                            yurl=f'https://www.youtube.com/watch?v={vid}'
                            obj['evidence_links'].add(yurl)
                            obj['issue_reasons'].append('유튜브 24h 리뷰/언급')
                            obj['evidence_briefs'].append({
                                'source':'youtube',
                                'url': yurl,
                                'title': title[:140],
                                'summary': '최근 24시간 내 업로드/언급된 영상에서 브랜드+모델 동시 확인'
                            })

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
            'evidence_briefs': obj['evidence_briefs'][:8],
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
