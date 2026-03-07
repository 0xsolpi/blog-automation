# Nami Image URL Contract (Mandatory)

목표: Robin 업로드 시 이미지 404/엑박 0건.

## 절대 규칙
1. **URL 수동 생성 금지**
   - `https://0xsolpi.com/wp-content/uploads/...` 같은 문자열 조합 금지
2. **작성 단계에서는 placeholder 우선**
   - 본문 이미지: `{{WP_IMAGE_<key>}}`
   - `image_manifest.placeholder_to_file` 1:1 완전 매핑 필수
3. **이미지 키 네이밍 고정 (run/post scoped)**
   - 공통키(`review1_img1` 등) 단독 사용 금지
   - `run_id + post_slug + key` 형태의 고유 키 필수
   - 예: `20260304-2349_rank1_kf94_review1_img1`
4. **wp-ready 출구 조건**
   - `./images`, `../` 0건
   - 미매핑 placeholder 0건
   - `your-domain.com` 0건

## 허용 도메인 정책
- 허용: `0xsolpi.com`, `cdn.solpi.blog`
- 그 외 도메인 금지

## handoff 요구 필드 (nami_to_zoro notes)
- `wp_ready_markdown_paths`
- `image_manifest_paths`
- `placeholder_to_file` (필수)
- `placeholder_to_sha256` (필수, 파일 무결성 검증용)
- (필수) `final_image_map` : `placeholder -> final_url` 확정 매핑
- (필수) `final_image_http_status` : 각 `final_url`의 HTTP 상태코드(200만 허용)

## 실패 처리
- 위 규칙 1개라도 위반 시 zoro에 PASS 요청 금지
- `FIX`로 자체 재생성 후 재검증
