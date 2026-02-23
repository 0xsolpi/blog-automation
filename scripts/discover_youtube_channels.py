#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, time
from datetime import datetime, timezone
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / '.env'
OUT = ROOT / 'data' / 'sources' / 'youtube_channels.json'

SEED_QUERIES = [
    '내돈내산 추천', '뷰티 추천템', '가전 리뷰', '생활용품 추천', '쿠팡 추천템',
    '주방템 추천', '자취템 추천', '육아템 추천', '핫템 리뷰', '올영 추천'
]


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


def yt_search_channels(key: str, q: str, max_results=20):
    url='https://www.googleapis.com/youtube/v3/search'
    params={
        'part':'snippet', 'type':'channel', 'q':q, 'regionCode':'KR', 'relevanceLanguage':'ko',
        'maxResults':max_results, 'key':key
    }
    r=requests.get(url, params=params, timeout=20)
    if r.status_code!=200:
        return []
    data=r.json()
    out=[]
    for it in data.get('items',[]):
        cid=(it.get('id',{}) or {}).get('channelId','')
        sn=it.get('snippet',{})
        if cid:
            out.append({'channelId':cid,'title':sn.get('title',''),'description':sn.get('description','')})
    return out


def yt_popular_videos_channels(key: str, max_results=50):
    url='https://www.googleapis.com/youtube/v3/videos'
    params={
        'part':'snippet', 'chart':'mostPopular', 'regionCode':'KR', 'videoCategoryId':'0',
        'maxResults':max_results, 'key':key
    }
    r=requests.get(url, params=params, timeout=20)
    if r.status_code!=200:
        return []
    data=r.json()
    out=[]
    for it in data.get('items',[]):
        sn=it.get('snippet',{})
        cid=sn.get('channelId','')
        if cid:
            out.append({'channelId':cid,'title':sn.get('channelTitle',''),'description':''})
    return out


def yt_channels_stats(key: str, ids: list[str]):
    if not ids:
        return {}
    url='https://www.googleapis.com/youtube/v3/channels'
    params={'part':'snippet,statistics','id':','.join(ids[:50]),'key':key}
    r=requests.get(url, params=params, timeout=20)
    if r.status_code!=200:
        return {}
    data=r.json()
    out={}
    for it in data.get('items',[]):
        cid=it.get('id','')
        st=it.get('statistics',{})
        sn=it.get('snippet',{})
        out[cid]={
            'subscriberCount':int(st.get('subscriberCount','0') or 0),
            'videoCount':int(st.get('videoCount','0') or 0),
            'title':sn.get('title',''),
            'publishedAt':sn.get('publishedAt','')
        }
    return out


def main():
    load_env(ENV)
    key=os.getenv('YOUTUBE_API_KEY','').strip()
    if not key:
        raise SystemExit('YOUTUBE_API_KEY missing')

    candidates={}
    for q in SEED_QUERIES:
        rows=yt_search_channels(key,q,max_results=25)
        for r in rows:
            candidates[r['channelId']]=r
        time.sleep(0.15)

    # fallback: if search seeds are weak, use KR popular videos channels
    if len(candidates) < 30:
        for r in yt_popular_videos_channels(key, max_results=50):
            candidates[r["channelId"]]=r

    ids=list(candidates.keys())
    stats={}
    for i in range(0,len(ids),50):
        stats.update(yt_channels_stats(key, ids[i:i+50]))
        time.sleep(0.15)

    keep=[]
    for cid,base in candidates.items():
        st=stats.get(cid)
        if not st:
            continue
        if st['subscriberCount'] < 1_000_000:
            continue
        keep.append({
            'channelId':cid,
            'title':st['title'] or base.get('title',''),
            'subscriberCount':st['subscriberCount'],
            'videoCount':st['videoCount'],
            'discoveredAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
        })

    keep=sorted(keep,key=lambda x:x['subscriberCount'],reverse=True)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(keep,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'ok':True,'discovered':len(keep),'out':str(OUT)},ensure_ascii=False))

if __name__=='__main__':
    main()
