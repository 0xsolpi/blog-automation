#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INP = ROOT / 'data' / 'trends' / 'luffy_output.json'
OUT = ROOT / 'data' / 'handoff' / 'nere_to_ace.json'


def _build_selection_reason(it: dict) -> dict:
    src_mix = it.get('source_mix', {}) or {}
    score = float(it.get('score', 0) or 0)
    mentions = int(it.get('mention_count_24h', 0) or 0)
    issue_reason = it.get('issue_reason', '')

    source_signals = []
    for src, label in [
        ('naver_shop', '네이버쇼핑'),
        ('naver_news', '뉴스'),
        ('naver_blog', '블로그'),
        ('youtube', '유튜브'),
    ]:
        c = int(src_mix.get(src, 0) or 0)
        if c > 0:
            source_signals.append(f"{label} {c}건")

    bullets = []
    if issue_reason:
        bullets.append(issue_reason)
    if source_signals:
        bullets.append('근거 출처 분포: ' + ', '.join(source_signals))
    bullets.append(f"24시간 언급량 {mentions}건")
    bullets.append(f"내부 트렌드 점수 {score:.1f}")

    return {
        'one_line': issue_reason or f"24시간 내 다중 출처 신호(언급 {mentions}건, 점수 {score:.1f})",
        'score': score,
        'mention_count_24h': mentions,
        'source_signals': source_signals,
        'bullets': bullets,
    }


def main():
    if not INP.exists():
        raise SystemExit(f'missing input: {INP}')
    src=json.loads(INP.read_text(encoding='utf-8'))
    run_id=src.get('run_id') or datetime.now().strftime('%Y%m%d-%H%M%S')

    items=[]
    for it in src.get('items',[]):
        brand=it.get('brand','')
        model=it.get('model_name','')
        if not brand or not model:
            continue
        items.append({
            'entity_key': it.get('entity_key',''),
            'trend_topic': it.get('canonical_product_name',''),
            'canonical_product_name': it.get('canonical_product_name',''),
            'brand': brand,
            'model_name': model,
            'mention_count_24h': it.get('mention_count_24h',0),
            'score': it.get('score', 0),
            'selection_reason': _build_selection_reason(it),
            'issue_reason': it.get('issue_reason', ''),
            'evidence_links': it.get('evidence_links',[])[:5],
            'evidence_briefs': it.get('evidence_briefs', [])[:3],
            'source_mix': it.get('source_mix',{}),
            'search_queries_seed': [
                f"{brand} {model}",
                f"{brand} {it.get('canonical_product_name','')}",
                model
            ],
            'precheck_confidence': round(min(0.99, 0.5 + it.get('score',0)/200),2)
        })

    payload={
        'run_id': run_id,
        'from': 'nere',
        'to': 'ace',
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'task': '쿠팡파트너스 매칭 검증',
        'acceptance_rules': {
            'min_precheck_confidence': 0.7,
            'require_brand_and_model': True,
            'require_coupang_partner_url': True
        },
        'items': items
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'ok':True,'count':len(items),'out':str(OUT)},ensure_ascii=False))


if __name__=='__main__':
    main()
