# 실행 방법 (MVP)

## 1) 승인 전 파이프라인 실행 (업로드 차단 확인)

```bash
./scripts/run_pipeline.sh
```

## 2) Admin 승인 후 실행 (업로드 단계 포함)

```bash
./scripts/run_pipeline.sh --admin-approved
```

## 3) 결과 확인

- `runs/<run_id>/manifest.json`
- `runs/<run_id>/events.jsonl`
- `runs/<run_id>/failures.jsonl`
- `data/*` 산출물
