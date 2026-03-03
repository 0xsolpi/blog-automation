#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path


def nere_candidate_report(payload: dict) -> str:
    reviews = payload.get("reviews", [])
    pass_n = sum(1 for r in reviews if r.get("result") == "PASS")
    fix_n = sum(1 for r in reviews if r.get("result") == "FIX")
    hold_n = sum(1 for r in reviews if r.get("result") == "HOLD")
    lines = [
        "📌 오늘 릴리즈 후보 보고",
        f"총 후보: {len(reviews)}건",
        f"✅ 승인 가능: {pass_n}건",
        f"⚠️ 조건부: {fix_n}건",
        f"❌ 반려: {hold_n}건",
        "",
    ]
    for r in reviews:
        label = {"PASS": "✅ 승인", "FIX": "⚠️ 조건부", "HOLD": "❌ 반려"}.get(r.get("result"), "⚠️ 조건부")
        lines += [
            f"[{r.get('title','(제목없음)')}]",
            f"- 이슈 출처: {r.get('issue_source','미기재')}",
            f"- 한줄 요약: {r.get('summary','미기재')}",
            f"- 쿠팡 링크 상태: {r.get('coupang_link_status','재확인 필요')}",
            f"- 전환 구조 적절성: {r.get('conversion_fit','수정 필요')}",
            f"- 리스크 레벨: {r.get('risk_level','🟡')}",
            f"- 네레 판정: {label}",
            "",
        ]
    lines.append("👉 업로드 승인 여부 회신 부탁드립니다.")
    return "\n".join(lines)


def robin_done_report(payload: dict) -> str:
    pubs = payload.get("published", [])
    lines = ["📌 업로드 완료 보고", f"총 업로드: {len(pubs)}건", ""]
    for p in pubs:
        lines += [
            f"- 제목: {p.get('title','')}",
            f"- 게시 URL: {p.get('post_url','')}",
            f"- 발행 일시: {p.get('published_at','')}",
            f"- 카테고리: {p.get('category','')}",
            f"- 태그 목록: {', '.join(p.get('tags',[]) or [])}",
            f"- 쿠팡 링크 정상 여부: {p.get('coupang_link_status','재확인 필요')}",
            f"- 이미지 정상 표시 여부: {p.get('image_status','재확인 필요')}",
            f"- 특이사항: {p.get('note','')}",
            "",
        ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", choices=["candidate", "published"], required=True)
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    text = nere_candidate_report(payload) if args.type == "candidate" else robin_done_report(payload)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(text, encoding="utf-8")
    print(json.dumps({"ok": True, "type": args.type, "output": args.output}, ensure_ascii=False))


if __name__ == "__main__":
    main()
