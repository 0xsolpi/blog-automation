#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict
from urllib.parse import urlparse
import requests

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / '.env'
OUT_RAW = ROOT / 'data' / 'trends' / 'luffy2_mentions.raw.json'
OUT_CURATED = ROOT / 'data' / 'trends' / 'luffy2_mentions.curated.json'

CELEBS = ["아이유","장원영","카리나","안유진","한소희","박보영","유재석","기안84","덱스","제니","지수","로제","정국","차은우","임영웅","이효리","화사","선미","박은빈","김지원","사쿠라","윈터"]
PRODUCT_TERMS = ["쿠션","선크림","립","앰플","향수","로봇청소기","정수기","이어폰","노트북","가방","신발","청소기","틴트","파운데이션"]
SNS_TERMS = ["인스타","SNS","틱톡","유튜브","쇼츠","바이럴","화제","품절"]
BROADCAST_TERMS = ["방송","예능","드라마","협찬","착용","사용템","왓츠인마이백","홈쇼핑"]
BRANDS = ["삼성","LG","애플","샤오미","로보락","다이슨","필립스","헤라","라네즈","설화수","닥터지","클리오","롬앤","조선미녀","아누아","에이지투웨니스","나이키","아디다스","샤넬","디올"]

TRUSTED_DOMAIN_HINTS = ["entertain.naver.com","vogue.co.kr","esquirekorea.co.kr","allurekorea.com","cosmopolitan.co.kr","wkorea.com"]
NOISY_WORDS = ["TOP3","TOP10","총정리","브리프","속보","단독","핫딜","특가"]


def load_env(path: Path):
    if not path.exists(): return
    for line in path.read_text(encoding='utf-8').splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        k,v=line.split('=',1)
        if k and k not in os.environ: os.environ[k]=v.strip()


def clean(s: str) -> str:
    s = re.sub(r'<[^>]+>', ' ', s or '')
    s = s.replace('&quot;',' ')
    s = re.sub(r'[^0-9A-Za-z가-힣\s\-/+]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def domain(url: str) -> str:
    try: return urlparse(url).netloc.lower()
    except Exception: return ''


def search_naver(api: str, cid: str, sec: str, query: str, display: int = 8) -> List[Dict]:
    url = f"https://openapi.naver.com/v1/search/{api}.json"
    headers = {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec}
    params = {"query": query, "display": display, "sort": "date"}
    r = requests.get(url, headers=headers, params=params, timeout=20)
    if r.status_code != 200: return []
    return r.json().get('items', [])


def youtube_search(key: str, q: str, hours: int = 24, max_results: int = 8) -> List[Dict]:
    url='https://www.googleapis.com/youtube/v3/search'
    published_after=(datetime.now(timezone.utc)-timedelta(hours=hours)).isoformat().replace('+00:00','Z')
    params={"part":"snippet","q":q,"type":"video","maxResults":max_results,"order":"date","regionCode":"KR","relevanceLanguage":"ko","publishedAfter":published_after,"key":key}
    r=requests.get(url,params=params,timeout=20)
    if r.status_code!=200: return []
    return r.json().get('items',[])




def parse_naver_time(item: Dict, api: str):
    if api == 'news':
        raw = (item.get('pubDate') or '').strip()
        if raw:
            for fmt in ['%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z']:
                try:
                    dt = datetime.strptime(raw, fmt)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt.astimezone(timezone.utc)
                except Exception:
                    pass
    if api == 'blog':
        raw = (item.get('postdate') or '').strip()  # YYYYMMDD
        if re.fullmatch(r'\d{8}', raw):
            try:
                dt = datetime.strptime(raw, '%Y%m%d').replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
    return None


def is_recent_naver(item: Dict, api: str, hours: int) -> bool:
    dt = parse_naver_time(item, api)
    if not dt:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return dt >= cutoff

def detect_brand(text: str) -> str:
    for b in BRANDS:
        if b in text: return b
    return ''


def detect_model(text: str) -> str:
    t=text.upper()
    for pat in [r'\b[A-Z]{1,4}-?[A-Z0-9]{3,12}\b', r'\b\d{2}[NC]\d\b']:
        m=re.search(pat,t)
        if m:
            x=m.group(0)
            if x in {'SNS','LIVE','BEST','TOP10','QUOT','JENNIE','SOOYAAA','K-EYES','WAY','AMP','LIP','TOP3'}: continue
            if re.fullmatch(r'SPF\d{2}',x): continue
            if re.fullmatch(r'\d{6,}', x): continue
            return x
    return ''


def detect_category(text: str) -> str:
    if any(k in text for k in ["쿠션","선크림","립","앰플","틴트","파운데이션","향수"]): return "화장품"
    if any(k in text for k in ["로봇청소기","정수기","이어폰","노트북","청소기"]): return "가전/디지털"
    if any(k in text for k in ["가방","신발","착용"]): return "패션"
    return "기타"


def detect_product_name(text: str) -> str:
    toks=text.split()
    for i,t in enumerate(toks):
        if any(p in t for p in PRODUCT_TERMS):
            left=toks[i-1] if i>0 else ''
            cand=(left+' '+t).strip()
            if len(cand) < 2: continue
            if any(bad in cand for bad in ['비롯해','상단','밑단','추가라니','웃으시라고','터지는']): continue
            return cand
    return ''


def classify(title: str) -> str:
    if any(k in title for k in BROADCAST_TERMS): return '방송노출'
    if any(k in title for k in SNS_TERMS): return 'SNS급등'
    if any(c in title for c in CELEBS): return '연예인'
    return ''


def pass_filter(title: str, link: str) -> bool:
    if not any(p in title for p in PRODUCT_TERMS): return False
    has_celeb = any(c in title for c in CELEBS)
    has_context = any(k in title for k in SNS_TERMS + BROADCAST_TERMS)
    if not (has_celeb or has_context): return False
    bad_words=['야구','축구','대선','정치','국회','증시','주가','MLB','KBO']
    if any(b in title for b in bad_words): return False
    if not link: return False
    return True


def score_item(item: Dict) -> int:
    t=item.get('mentioned_content','')
    link=item.get('related_link','')
    d=domain(link)
    s=0
    if any(c in t for c in CELEBS): s += 3
    if any(k in t for k in SNS_TERMS + BROADCAST_TERMS): s += 2
    if item.get('product_name'): s += 2
    if item.get('product_brand'): s += 2
    if item.get('product_model'): s += 2
    if item.get('product_category') != '기타': s += 1
    if item.get('source') == 'youtube': s += 1
    if any(h in d for h in TRUSTED_DOMAIN_HINTS): s += 2
    if any(n in t for n in NOISY_WORDS): s -= 2
    return s


def rec(title: str, summary: str, link: str, source: str) -> Dict:
    t=clean(title); s=clean(summary); text=f"{t} {s}"
    r={
        'product_name': detect_product_name(text),
        'product_model': detect_model(text),
        'product_brand': detect_brand(text),
        'product_category': detect_category(text),
        'mentioned_content': t[:220],
        'related_link': link,
        'mention_type': classify(t),
        'source': source,
    }
    r['score'] = score_item(r)
    return r


def main():
    load_env(ENV)
    cid=os.getenv('NAVER_CLIENT_ID','').strip(); sec=os.getenv('NAVER_CLIENT_SECRET','').strip(); yk=os.getenv('YOUTUBE_API_KEY','').strip()
    if not cid or not sec: raise SystemExit('NAVER keys missing')
    ap=argparse.ArgumentParser(); ap.add_argument('--hours',type=int,default=24); ap.add_argument('--limit',type=int,default=80); ap.add_argument('--curated-limit',type=int,default=25); args=ap.parse_args()

    rows=[]
    for celeb in CELEBS[:14]:
        for term in PRODUCT_TERMS[:10]:
            for q in [f"{celeb} {term}", f"{celeb} {term} 방송", f"{celeb} {term} 인스타"]:
                for it in search_naver('news',cid,sec,q,6):
                    if not is_recent_naver(it, 'news', args.hours):
                        continue
                    title=clean(it.get('title','')); link=it.get('link',''); desc=it.get('description','')
                    if pass_filter(title,link): rows.append(rec(title,desc,link,'naver_news'))
                for it in search_naver('blog',cid,sec,q,4):
                    if not is_recent_naver(it, 'blog', args.hours):
                        continue
                    title=clean(it.get('title','')); link=it.get('link',''); desc=it.get('description','')
                    if pass_filter(title,link): rows.append(rec(title,desc,link,'naver_blog'))

    if yk:
        for celeb in CELEBS[:10]:
            for q in [f"{celeb} 추천템", f"{celeb} 왓츠인마이백", f"{celeb} 사용템"]:
                for it in youtube_search(yk,q,args.hours,6):
                    sn=it.get('snippet',{}); title=clean(sn.get('title','')); desc=clean(sn.get('description',''))
                    vid=(it.get('id',{}) or {}).get('videoId','')
                    if not vid: continue
                    link=f'https://www.youtube.com/watch?v={vid}'
                    if pass_filter(title,link): rows.append(rec(title,desc,link,'youtube'))

    seen=set(); out=[]
    for r in rows:
        if not r.get('mention_type'): continue
        key=(r['related_link'],r['mentioned_content'])
        if key in seen: continue
        seen.add(key); out.append(r)

    pr={'방송노출':3,'SNS급등':2,'연예인':1}
    out.sort(key=lambda x:(x.get('score',0), pr.get(x['mention_type'],0)), reverse=True)

    raw=out[:args.limit]
    curated=[x for x in out if x.get('score',0) >= 6 and (x.get('product_name') or x.get('product_brand') or x.get('product_model'))][:args.curated_limit]

    meta={
        'run_id':datetime.now().strftime('%Y%m%d-%H%M%S'),
        'agent':'luffy2',
        'generated_at':datetime.now().isoformat(timespec='seconds'),
        'time_window_hours':args.hours,
    }

    OUT_RAW.parent.mkdir(parents=True,exist_ok=True)
    OUT_RAW.write_text(json.dumps({**meta,'count':len(raw),'items':raw},ensure_ascii=False,indent=2),encoding='utf-8')
    OUT_CURATED.write_text(json.dumps({**meta,'count':len(curated),'items':curated},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'ok':True,'raw_count':len(raw),'curated_count':len(curated),'raw_out':str(OUT_RAW),'curated_out':str(OUT_CURATED)},ensure_ascii=False))

if __name__=='__main__':
    main()
