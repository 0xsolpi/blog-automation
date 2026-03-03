# Publish Quality Gate (Robin)

발행 전 아래 4개 모두 통과해야 한다.

## Gate Checklist
- [ ] 본문에 Markdown raw 잔존 없음 (`# `, `## `, `|---|---|` 등)
- [ ] `{{WP_IMAGE_*}}` placeholder 0건
- [ ] 내부링크 `.md`/`../` 0건
- [ ] 대표이미지 지정 완료

## Fail Policy
- 하나라도 실패하면 발행 금지
- `failures_<run_id>.json` 기록
- 상태를 `ROBIN_BLOCKED`로 전환

## Success Policy
- 발행 후 URL/게시시각/대표이미지/스냅샷 검증 결과 회신
