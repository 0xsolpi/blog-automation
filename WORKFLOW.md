# 네레 실제 일처리 방법 (운영 SOP)

## 현재 운영 버전(vCurrent) — 12단계 고정

1. **루피 리서치 트리거(이중 방식)**
   - **1-1 수동 트리거**: Admin → 루피 아이템 리서치 명령
   - **1-2 자동 트리거**: 매일 06:10(KST) 루피 자동 리서치 실행 후 아이템 목록을 텔레그램 전달
2. **루피**: 후보 수집 후 **Admin에게 선택 요청**
3. **Admin**: 아이템 선택 확정
4. **루피 → 에이스**: Admin 선택 아이템 전달
5. **에이스**: 선택 아이템 검증/정리
6. **에이스 → 나미**: 정리 결과 전달
7. **나미**: 글 작성 + 업로드 패키지 구성
8. **나미 → 조로**: 검수 요청
9. **조로 PASS 건 → 네레**: 업로드 가능 여부 게이트
10. **네레 → Admin**: 업로드 승인 여부 확인
11. **승인 시 네레 → 로빈**: 업로드 명령
12. **로빈**: 포스트 업로드 후 결과 회신

---

## 운영 세부 규칙

### 0) 시작 조건
- Admin 지시 수신 시 run_id 생성 (`YYYYMMDD-HHMMSS`)
- 핸드오프 기본 경로 생성: `data/handoff/<run_id>/`

### 1) 루피 단계
- 산출:
  - 후보 요청용: `nere_to_admin_candidates.json` (또는 보고서)
  - 선택 반영 후: `luffy_to_ace.json`
- Admin 선택 전에는 에이스로 넘기지 않음

### 2) 에이스 단계
- 산출 기대: `ace_to_nami.json`
- 검증: `python3 scripts/validate_handoff.py --stage ace_to_nami --input data/handoff/<run_id>/ace_to_nami.json`
- 트리거 누락 방지 필수 정책:
  - 상태머신 `RECEIVED -> QUEUED -> RUNNING -> DONE|BLOCKED`
  - enqueue/실행 확인 전 RUNNING(STARTED) 송신 금지
  - RECEIVED 후 120초 내 RUNNING 미도달 시 자동 재큐잉 + IN_PROGRESS 보고
  - DONE_NOTIFY 성공 전 DONE 금지

### 3) 나미 단계
- 산출 기대: `nami_to_zoro.json`
- 검증: `python3 scripts/validate_handoff.py --stage nami_to_zoro --input data/handoff/<run_id>/nami_to_zoro.json`
- 추가 필수:
  - `category`, `tags` 포함
  - `image_manifest` 포함 (`featured_image`, `body_images`, `placeholder_to_file`)
  - 이미지 파일명 유니크 (`run_id-rank-purpose` 권장)
  - 본문 placeholder(`{{WP_IMAGE_*}}`)와 매핑 1:1 보장

### 4) 조로 단계
- 산출 기대: `zoro_to_nere.json`
- PASS/FIX/HOLD 명확 판정

### 5) 네레 승인 게이트
- PASS 건만 후보 보고 생성 후 Admin 승인 요청
- 네레 판정은 반드시 `✅ 승인 / ⚠️ 조건부 / ❌ 반려`
- 리스크 레벨(🟢/🟡/🔴) 필수 포함

### 6) 로빈 업로드/회수
- Admin 승인 건만 업로드
- 산출 기대: `robin_to_nere.json`
- 회수 필수: URL / 게시상태 / 실패여부 / run_id

## 승인 게이트 고정 순서
**조로 → 네레 → Admin → 로빈 → 네레 → Admin**
