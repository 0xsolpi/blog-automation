#!/usr/bin/env python3
import argparse, json, os, uuid
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

STAGES = [
    "COLLECTING_TRENDS",
    "VALIDATING_CPA",
    "WRITING_DRAFTS",
    "QA_REVIEW",
    "ADMIN_APPROVAL_PENDING",
    "READY_TO_PUBLISH",
    "PUBLISHED",
]


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def ensure_dirs(run_dir: Path):
    run_dir.mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "trends").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "verified").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "drafts").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "review").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "published").mkdir(parents=True, exist_ok=True)


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def event(run_dir: Path, stage: str, message: str, extra=None):
    payload = {
        "ts": now_iso(),
        "stage": stage,
        "message": message,
    }
    if extra:
        payload["extra"] = extra
    append_jsonl(run_dir / "events.jsonl", payload)


def fail(run_dir: Path, stage: str, item_slug: str, reason: str):
    payload = {
        "ts": now_iso(),
        "stage": stage,
        "item_slug": item_slug,
        "reason": reason,
    }
    append_jsonl(run_dir / "failures.jsonl", payload)


def mock_collect():
    items = [
        {
            "item_name": "무선 핸디 청소기",
            "issue_reason": "집정리/신학기 시즌으로 소형 가전 관심 급증",
            "evidence_links": [
                "https://trends.google.com/",
                "https://search.naver.com/",
            ],
            "score": 84,
            "observed_at": now_iso(),
        },
        {
            "item_name": "휴대용 보조배터리",
            "issue_reason": "여행/외출 증가로 충전 액세서리 수요 증가",
            "evidence_links": [
                "https://trends.google.com/",
            ],
            "score": 79,
            "observed_at": now_iso(),
        },
    ]
    write_json(ROOT / "data" / "trends" / "top_items.json", items)
    return items


def mock_verify(items):
    verified = []
    for i, item in enumerate(items, start=1):
        slug = f"item-{i}"
        item2 = dict(item)
        item2.update(
            {
                "item_slug": slug,
                "coupang_available": True,
                "coupang_partner_url": f"https://link.coupang.com/a/mock{100+i}",
                "checked_at": now_iso(),
            }
        )
        verified.append(item2)
    write_json(ROOT / "data" / "verified" / "verified_items.json", verified)
    return verified


def mock_write_drafts(items):
    outputs = []
    for item in items:
        slug = item["item_slug"]
        title = f"요즘 왜 뜨나? {item['item_name']} 이슈 정리"
        body = f"""# {title}

최근 이슈의 중심에는 **{item['item_name']}** 가 있습니다. 실제 검색량/관심도 지표에서 상승 흐름이 관찰되고 있으며, 생활 밀착형 사용성이 재조명되고 있습니다.\

이 아이템이 주목받는 핵심 이유는 {item['issue_reason']} 입니다. 관련 근거는 아래 링크에서 확인할 수 있습니다: {', '.join(item['evidence_links'])}.\

실사용 관점에서 보면, 가격 대비 편의성과 즉시 체감 가능한 효용이 크다는 점이 반복적으로 언급됩니다. 특히 입문자도 부담 없이 접근할 수 있다는 점이 강점입니다.\

구매를 고려한다면 아래 파트너스 링크에서 옵션과 가격을 먼저 비교해보세요: {item['coupang_partner_url']}
"""
        path = ROOT / "data" / "drafts" / f"{slug}.md"
        path.write_text(body, encoding="utf-8")
        outputs.append({"item_slug": slug, "path": str(path.relative_to(ROOT))})
    return outputs


def mock_review(drafts):
    reports = []
    for d in drafts:
        reports.append(
            {
                "item_slug": d["item_slug"],
                "qa_status": "pass_with_minor_edits",
                "reasons": ["문맥 자연스러움 양호", "근거/링크 포함"],
                "required_fixes": ["제목 클릭 유도 표현 과장 여부 최종 점검"],
            }
        )
    write_json(ROOT / "data" / "review" / "review_reports.json", reports)
    return reports


def mock_publish(review_reports, require_approval=True, approved=False):
    if require_approval and not approved:
        return None
    out = []
    for r in review_reports:
        if r["qa_status"] in ("pass", "pass_with_minor_edits"):
            out.append(
                {
                    "item_slug": r["item_slug"],
                    "post_id": f"mock-{uuid.uuid4().hex[:8]}",
                    "post_url": f"https://example.com/{r['item_slug']}",
                    "published_at": now_iso(),
                    "status": "success",
                }
            )
    write_json(ROOT / "data" / "published" / "publish_reports.json", out)
    return out


def run(args):
    run_id = args.run_id or datetime.now().strftime("%Y%m%d-%H%M") + "-" + uuid.uuid4().hex[:6]
    run_dir = ROOT / "runs" / run_id
    ensure_dirs(run_dir)

    manifest = {
        "run_id": run_id,
        "started_at": now_iso(),
        "mode": args.mode,
        "admin_approved": args.admin_approved,
        "status": "running",
        "stages": [],
    }

    # Stage 1
    event(run_dir, STAGES[0], "루피 단계 시작")
    items = mock_collect() if args.mode == "mock" else []
    manifest["stages"].append({"stage": STAGES[0], "status": "done", "count": len(items)})

    # Stage 2
    event(run_dir, STAGES[1], "에이스 단계 시작")
    verified = mock_verify(items) if args.mode == "mock" else []
    manifest["stages"].append({"stage": STAGES[1], "status": "done", "count": len(verified)})

    # Stage 3
    event(run_dir, STAGES[2], "나미 단계 시작")
    drafts = mock_write_drafts(verified) if args.mode == "mock" else []
    manifest["stages"].append({"stage": STAGES[2], "status": "done", "count": len(drafts)})

    # Stage 4
    event(run_dir, STAGES[3], "조로 단계 시작")
    reviews = mock_review(drafts) if args.mode == "mock" else []
    manifest["stages"].append({"stage": STAGES[3], "status": "done", "count": len(reviews)})

    # Stage 5
    event(run_dir, STAGES[4], "Admin 승인 대기")
    manifest["stages"].append({"stage": STAGES[4], "status": "done", "approved": args.admin_approved})

    # Stage 6 + 7
    if args.admin_approved:
        event(run_dir, STAGES[5], "업로드 준비 완료")
        manifest["stages"].append({"stage": STAGES[5], "status": "done"})

        event(run_dir, STAGES[6], "로빈 업로드 시작")
        published = mock_publish(reviews, require_approval=True, approved=True)
        manifest["stages"].append({"stage": STAGES[6], "status": "done", "count": len(published or [])})
        manifest["status"] = "published"
    else:
        event(run_dir, STAGES[5], "승인 전 업로드 금지")
        manifest["stages"].append({"stage": STAGES[5], "status": "blocked"})
        manifest["status"] = "awaiting_admin_approval"

    manifest["finished_at"] = now_iso()
    write_json(run_dir / "manifest.json", manifest)

    print(json.dumps({"ok": True, "run_id": run_id, "status": manifest["status"]}, ensure_ascii=False))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Blog automation orchestrator MVP")
    p.add_argument("--run-id", default="", help="Optional run id")
    p.add_argument("--mode", choices=["mock", "live"], default="mock")
    p.add_argument("--admin-approved", action="store_true", help="Allow publish stage")
    args = p.parse_args()
    run(args)
