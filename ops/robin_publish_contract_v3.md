# Robin Publish Contract v3 (Mandatory)

## Objective
깨진 발행 방지: 변환/치환/링크 검증을 통과한 결과만 발행.

## Steps (strict order)
1) `wp-ready.md` 로드
2) 이미지 업로드 후 placeholder 치환 (`{{WP_IMAGE_*}} -> https://...`)
3) 내부링크 정규화 (`.md`, `../` 금지)
4) Markdown -> WordPress block HTML(또는 렌더된 HTML) 변환
5) `scripts/publish_preflight.py` 실행 (최종 발행 본문 기준)
6) preflight 통과 시에만 발행
7) 발행 후 URL/시각/대표이미지/스냅샷 검증

## Hard Fail
아래 중 1개라도 발견 시 발행 금지 + failures 기록:
- placeholder 잔존
- `.md`/`../` 링크
- raw markdown 헤더/테이블 노출
- 대표이미지 미지정

## CLI
```bash
python3 scripts/publish_preflight.py --files <final_rendered_content_files...> --out state/preflight_<run_id>.json
```
