#!/usr/bin/env python3
from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INP = ROOT / 'data' / 'trends' / 'luffy_output.json'
OUT = ROOT / 'data' / 'handoff' / 'nere_to_ace.json'


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
            'evidence_links': it.get('evidence_links',[])[:5],
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
