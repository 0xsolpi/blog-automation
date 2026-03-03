# HANDOFF_SCHEMA.md — nere control contract

## 공통 경로 규칙 (통일)
모든 단계 산출물은 아래 경로를 사용한다.

- `data/handoff/<run_id>/luffy_to_ace.json`
- `data/handoff/<run_id>/ace_to_nami.json`
- `data/handoff/<run_id>/nami_to_zoro.json`
- `data/handoff/<run_id>/zoro_to_nere.json`
- `data/handoff/<run_id>/robin_to_nere.json`
- `data/handoff/<run_id>/nere_to_admin_candidates.json` (루피 후보를 네레가 Admin에게 전달)
- `data/handoff/<run_id>/admin_to_ace_selected.json` (Admin 확정본)
- `data/handoff/<run_id>/admin_to_ace_selected.template.json` (입력 템플릿)
- `data/handoff/<run_id>/nere_to_admin_candidate_report.md`
- `data/handoff/<run_id>/nere_to_admin_published_report.md`

## 공통 필수 메타
- run_id
- from
- to
- generated_at (ISO-8601)

## 승인 게이트 (최종)
`조로 → 네레 → Admin → 로빈 → 네레 → Admin`

1. zoro 검수 결과 수신(PASS/FIX/HOLD)
2. nere 후보 보고 생성 및 Admin 승인 요청
3. Admin 승인 건만 robin에 전달
4. robin 업로드 실행/결과 회신
5. nere 업로드 완료 보고 생성
6. Admin에게 최종 업로드 완료 보고

## 검증 스크립트
- `python3 scripts/validate_handoff.py --stage <stage> --input <file>`

### 이미지/업로드 재발 방지 규칙 (nami_to_zoro 필수)
- 각 포스트는 아래 필드를 반드시 포함한다:
  - `category` (string)
  - `tags` (non-empty array)
  - `image_manifest` (object)
- `image_manifest` 필수 구조:
  - `featured_image`: 대표 이미지 파일명
  - `body_images`: 본문 이미지 파일명 배열
  - `placeholder_to_file`: `{{WP_IMAGE_*}} -> 파일명` 매핑
- 파일명은 run_id/랭크 기준으로 유니크해야 한다. (중복 파일명 금지)
- 본문 내 `{{WP_IMAGE_*}}` placeholder는 반드시 `placeholder_to_file`에 1:1 매핑되어야 한다.
- 위 조건 불충족 시 네레 게이트에서 `HOLD` 처리한다.

stage:
- luffy_to_ace
- ace_to_nami
- nami_to_zoro
- zoro_to_nere
- robin_to_nere

## 텔레그램 보고 템플릿 생성
- 후보 보고:  
  `python3 scripts/render_telegram_report.py --type candidate --input data/handoff/<run_id>/zoro_to_nere.json --output data/handoff/<run_id>/nere_to_admin_candidate_report.md`
- 업로드 완료 보고:  
  `python3 scripts/render_telegram_report.py --type published --input data/handoff/<run_id>/robin_to_nere.json --output data/handoff/<run_id>/nere_to_admin_published_report.md`
