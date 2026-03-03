# 네레 실제 일처리 방법 (운영 SOP)

## 운영 모드
- `legacy`: 기존 12단계 handoff 중심 운영
- `v2-event`: run_id 상태파일 + 이벤트 로그 기반 운영 (권장)
- `autopilot-v1` (기본): 사장님 개입은 `리서치 요청` + `아이템 선택`만. 이후 포스팅 업로드까지 자동.

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

## autopilot-v1 고정 순서 (신규 기본)
**Admin(리서치 요청/아이템 선택) → 루피 → 에이스 → 나미 ↔ 조로(최대 3회 수정루프) → 네레 업로드 → Admin 최종 결과 보고**

> 운영 고정:
> - 사장님은 선택 이후 중간 동의/개입 없음
> - 중간 ACK/announce는 사용자 채널 발신 금지
> - 실패는 내부 재시도 최대 3회 후 `BLOCKED` 1회 보고
> - PASS + 정책검사 통과 시 즉시 발행
> - 로빈은 기본 비활성(로그/보조). 단, 업로드 SLA 위반 시 백업 워커로 자동 승격

### 업로드 무정지/무누락 강제 규칙 (No-Regression)
1) 업로드 시작 즉시 `STARTED` 이벤트 기록
2) 2분 무변화 시 Watchdog 경고 + 자동 재시도
3) 5분 내 `DONE(url, published_at)` 미달 시 자동 실패
4) 실패 2회면 즉시 `BLOCKED` + 백업 경로 자동 전환
5) 완료 보고 필수값: `post_url`, `published_at`, `render_check`
6) URL 없는 완료 보고는 무효(미완료 처리)
7) 단일 탭 실행, 완료 후 `tabs_cleanup: done` 필수

> 세부 기준 문서: `ops/no-regression_upload_safety_policy.md`

---

## v2-event 상태머신 (신규)
`COLLECTED -> SELECTED -> ACE_VALIDATING -> ACE_DONE -> NAMI_WRITING -> NAMI_DONE -> ZORO_REVIEWING -> ZORO_DONE -> NERE_DECISION -> ROBIN_PUBLISHING -> PUBLISHED`

### 에러/복구 상태
- `*_BLOCKED`: 외부 의존(브라우저 relay/tab/auth) 문제
- `*_FAILED`: 정책/검증 실패
- `RETRY_SCHEDULED`: 자동 재시도 예약

### 필수 공통 메타
- `run_id`, `from`, `to`, `generated_at`, `stage`, `retry_count`

### 운영 원칙
1) 채팅은 보고/승인용, 실행은 상태파일/이벤트로 진행
2) ACK SLA 20초, 미수신 시 1회 재전송
3) announce는 로그만 남기고 실행 트리거로 사용 금지
4) Robin 발행 전 `ops/publish_quality_gate.md` 4개 게이트 통과 필수
