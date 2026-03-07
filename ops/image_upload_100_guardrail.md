# Image Upload 100 Guardrail (Nami → Zoro → Robin)

목표: "게시는 됐는데 이미지 엑박"을 구조적으로 0건으로 만든다.

## 핵심 원칙
- **게시 성공 != 이미지 성공**
- 이미지는 아래 3단계가 모두 통과해야만 성공으로 인정한다.
  1) 업로드 실체 존재
  2) 본문 치환 정확성
  3) 렌더 가시성

---

## 0) 도메인 정책 (운영 현실 반영)
- 허용 이미지 도메인: `0xsolpi.com`, `cdn.solpi.blog`
- 그 외 외부 도메인 삽입 금지
- 권장: 가능하면 1차 기준은 `0xsolpi.com`으로 통일하되, CDN 라우팅/최적화가 활성화된 기간에는 `cdn.solpi.blog`를 정상 도메인으로 인정

---

## 1) Nami 단계 (작성/치환)
출구 조건(모두 충족):
- 상대경로 `./images` / `../` 0건
- URL 수동 조합 금지 (`.../wp-content/uploads/...` 패턴을 추정 생성 금지)
- `{{WP_IMAGE_*}}` placeholder는 반드시 `placeholder_to_file`에 1:1 매핑
- 최종 본문 이미지 URL은 업로드 실체 검증본만 사용
- 본문 이미지 URL이 모두 허용 도메인(`0xsolpi.com`, `cdn.solpi.blog`)
- image_manifest 이미지 수와 본문 이미지 수 일치

검증 명령 예시:
```bash
grep -E "\./images/|\.\./" <wp-ready.md>
grep -E "\{\{WP_IMAGE_" <wp-ready.md>
grep -oE 'https?://[^"\) ]+\.(jpg|jpeg|png|webp)' <wp-ready.md>
```

하나라도 실패하면 zoro handoff 금지.

---

## 2) Zoro 단계 (게이트)
PASS 조건에 아래를 추가한다:
- 상대경로 0건
- placeholder 미매핑 0건
- 허용 도메인 외 이미지 URL 0건
- URL 수동 조합 흔적 0건
- `final_image_map` 존재 + placeholder 1:1 완전 매핑
- 고유 키 규칙 충족(run/post scoped key)
- 이미지 샘플 3개 이상 HTTP 200 증거

미충족 시 반드시 FIX, 중대한 위반(수동 URL 조합/404 확인/매핑 누락)은 HOLD.

---

## 3) Robin 단계 (업로드/발행)
### A. Preflight (발행 전)
- wp-ready 재검증 3종(상대경로/placeholder/도메인)
- `final_image_map`과 본문 이미지 placeholder 1:1 일치 검증
- 공통키 fuzzy 검색 금지 (`review1_img1` 등 키워드 검색 기반 매칭 금지)
- 매핑 기반 URL 외 이미지 사용 금지
- 실패 시 `ROBIN_BLOCKED` + 실패 근거 파일 기록

### B. Publish (발행)
- 발행 수행

### C. Postflight (발행 직후, 성공 확정 전에 필수)
아래 모두 성공 시에만 SUCCESS:
1) post URL HTTP 200
2) 본문 이미지 URL 샘플 3개 이상 HTTP 200
3) 브라우저 렌더(본문) 엑박 없음

하나라도 실패하면 즉시 `ROBIN_BLOCKED`로 되돌림.

---

## 4) Nere 승인/보고 규칙
- 조로 PASS 후 반드시 Admin 승인 질의
- Admin 승인 전 업로드 금지
- Robin의 "published" 메시지만으로 성공 처리 금지
- Nere가 Postflight 3조건 확인 후에만 "업로드 완료" 보고

---

## 5) 장애 복구 표준 절차 (엑박 발견 시)
1) 게시물 즉시 비공개/수정모드 전환
2) 누락 이미지 재업로드
3) 본문 이미지 URL 재치환
4) Postflight 3조건 재검증
5) 통과 후 재공개

---

## 6) SLA/재시도
- 업로드 지시 후 5분 대기
- 무응답 시 재전송
- 5분 단위 재확인, 최대 2회 재전송
- 최종 실패는 BLOCKED 1회만 보고
