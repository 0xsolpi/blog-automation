# Publish Quality Gate (Robin)

발행 전 아래 4개 모두 통과해야 한다.

## Gate Checklist
- [ ] 본문에 Markdown raw 잔존 없음 (`# `, `## `, `|---|---|` 등)
- [ ] `{{WP_IMAGE_*}}` placeholder 0건
- [ ] 내부링크 `.md`/`../` 0건
- [ ] 대표이미지 지정 완료
- [ ] 본문 이미지 URL 전수 검사(최소 샘플 3개): DNS 해석 가능 + HTTP 200
- [ ] 본문 이미지 도메인 허용목록 일치 (`0xsolpi.com`, 운영 승인 CDN만 허용)
- [ ] `wp-json/wp/v2/media` 기준 핵심 이미지(최소 3개) 존재 확인
- [ ] 발행 URL 실존 확인(HTTP 200, 404 금지)

## Fail Policy
- 하나라도 실패하면 발행 금지
- `failures_<run_id>.json` 기록 (실패 URL/HTTP 코드/DNS 오류 포함)
- 상태를 `ROBIN_BLOCKED`로 전환
- Admin에는 "게시 성공" 문구 사용 금지 (복구중/차단중으로 보고)

## Success Policy
- 발행 후 아래 모두 확인되면 SUCCESS:
  1) post URL 200
  2) 본문 이미지 샘플 3개 이상 200
  3) 랜덤 1개 브라우저 렌더 확인(엑박 없음)
- 위 3개 증거(검증 로그/샘플 URL/시각) 포함하여 회신
