# 실행 방법 (MVP)

## 1) mock 실행 (검증용)

```bash
./scripts/run_pipeline.sh
./scripts/run_pipeline.sh --admin-approved
```

## 2) live 수집 모드 실행 (루피 단계 실제 RSS 수집)

```bash
./scripts/run_pipeline.sh --mode live
./scripts/run_pipeline.sh --mode live --admin-approved
```

## 3) 결과 확인

- `runs/<run_id>/manifest.json`
- `runs/<run_id>/events.jsonl`
- `runs/<run_id>/failures.jsonl`
- `data/trends/top_items.json`
- `data/verified/verified_items.json`
- `data/review/review_reports.json`

> 현재 live는 루피 수집 단계 중심이며,
> 에이스/나미/조로/로빈은 mock 처리입니다.


- live 수집은 `pubDate` 기준 최근 24시간 항목만 반영합니다.

## 4) API 키 사용 (.env)

```env
YOUTUBE_API_KEY=...
NAVER_CLIENT_ID=...
NAVER_CLIENT_SECRET=...
```

- YouTube: 최근 24시간 업로드 영상 기반 보조 신호
- Naver DataLab: 후보 키워드 트렌드 ratio 보정 신호
