# Robin Publish Contract v3 (Mandatory)

## Objective
깨진 발행 방지: 변환/치환/링크 검증을 통과한 결과만 발행.

## Steps (strict order)
1) `wp-ready.md` 로드
2) **WordPress Media API(`/wp-json/wp/v2/media`)로 원본 이미지 업로드**
3) 업로드 API 응답(`id`,`source_url`)으로 `final_image_map` 생성 (`placeholder -> source_url`, run/post scoped)
4) 이미지 치환은 **맵 기반 1:1 치환만 허용** (`{{WP_IMAGE_*}} -> source_url`)
5) 내부링크 정규화 (`.md`, `../` 금지)
6) Markdown -> WordPress block HTML(또는 렌더된 HTML) 변환
7) `scripts/publish_preflight.py` 실행 (최종 발행 본문 + image_manifest 기준)
   - 본문 검사: placeholder/상대경로/raw markdown 노출 차단
   - manifest 검사: `images[].local_path` 실파일 존재/읽기 가능/0바이트 아님
8) preflight 통과 시에만 발행
9) 발행 후 URL/시각/대표이미지/스냅샷 검증

## Hard Fail
아래 중 1개라도 발견 시 발행 금지 + failures 기록:
- placeholder 잔존
- `.md`/`../` 링크
- `your-domain.com` 더미 링크
- `./images/...` 상대경로 이미지
- raw markdown 헤더/테이블 노출
- 대표이미지 미지정
- Media API 업로드 응답(`id`,`source_url`) 미확인 이미지 존재
- API `source_url` 외 임의 URL(추정 경로/수동 조합 URL) 사용
- `final_image_map` 누락 또는 placeholder 불일치
- fuzzy 검색/유사 slug 기반 이미지 치환 시도 (`review1_img1` 등 키워드 검색 매칭)
- 타 run/post 이미지로 판단되는 URL 감지 시 (run/post prefix 불일치)

## CLI
```bash
python3 scripts/publish_preflight.py \
  --files <final_rendered_content_files...> \
  --manifests <image_manifest_files...> \
  --out state/preflight_<run_id>.json
```
