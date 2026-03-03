# Rearchitecture v2 Master Plan (Event-driven)

## Goal
세션 timeout/relay 불안정/announce 소음으로 인한 파이프라인 병목을 제거하고,
`run_id` 기준으로 **재현 가능 + 자동 복구 가능한** 운영 구조로 전환한다.

---

## 1) Core Principle
- 채팅은 보고/승인 전용
- 실행은 상태파일(state) + 이벤트파일(event) 기반
- 모든 단계는 `run_id` 단위 상태머신으로 진행

---

## 2) Target State Machine
`COLLECTED -> SELECTED -> ACE_VALIDATING -> ACE_DONE -> NAMI_WRITING -> NAMI_DONE -> ZORO_REVIEWING -> ZORO_DONE -> NERE_DECISION -> ROBIN_PUBLISHING -> PUBLISHED`

에러 분기:
- `*_BLOCKED` (외부 의존 문제: relay/tab/auth)
- `*_FAILED` (검증 실패/정책 위반)
- `RETRY_SCHEDULED`

---

## 3) File Contract (single source of truth)
- `state/runs/<run_id>.json` : 현재 상태, 담당자, 타임스탬프
- `events/<run_id>/<ts>_<event>.json` : 단계 이벤트 append-only
- `handoff/<run_id>/...` : 단계 산출물

필수 공통 메타:
- `run_id`, `from`, `to`, `generated_at`, `stage`, `retry_count`

---

## 4) Agent Contract
### Luffy
- 후보 12개 리서치 생성
- 완료 이벤트: `luffy.done`

### Ace
- `selected_item_numbers` 수신 시 검증 시작
- 완료 이벤트: `ace.done`

### Nami
- `ace.done` 수신 시 작성
- 완료 이벤트: `nami.done` + `nami_to_zoro.json`
- 금지: 내부링크 `.md`, `../` 상대경로

### Zoro
- `nami.done` 수신 시 검수
- 완료 이벤트: `zoro.done` (PASS/FIX/HOLD)

### Nere
- 승인 판정 + 리스크 라벨
- `approval.granted` 시 robin 호출

### Robin
- 업로드 워커 전용 (세션 대화와 분리)
- 선검증:
  - placeholder 0건
  - `.md`/`../` 링크 0건
  - 블록 렌더 스냅샷 OK
- 완료 이벤트: `robin.published`

---

## 5) Timeout Hardening
- ACK SLA: 20초
- 미수신 시 `retry=1` 자동 재전송
- 2회 실패 시 `*_BLOCKED` + 즉시 상위 보고
- announce 메시지는 이벤트 로그로만 저장, 채팅 전파 금지

---

## 6) Publish Quality Gate (mandatory)
발행 전 실패 조건:
1. Markdown 원문 토큰(`#`, `|---|---|`)가 본문 그대로 노출
2. `{{WP_IMAGE_*}}` placeholder 잔존
3. 내부링크 `.md` 또는 상대경로
4. 대표이미지 누락

한 개라도 해당 시 발행 금지 + `robin.blocked`.

---

## 7) Migration Plan (safe)
### Phase A (오늘)
- 규칙 문서 고정
- 상태파일/이벤트 디렉터리 도입
- run_id 상태머신 기록 시작

### Phase B
- 나미→조로 자동 트리거를 이벤트 기반으로 전환
- 로빈 업로드 워커를 별도 경량 세션으로 분리

### Phase C
- 대화형 ACK 최소화
- 대시보드/요약 리포트 자동 생성

---

## 8) Rollback
- 언제든 기존 세션 기반 handoff로 즉시 회귀 가능
- 조건: `PIPELINE_MODE=legacy`

---

## 9) Immediate next actions
1) `WORKFLOW.md`에 v2 상태머신 병기
2) `ops/publish_quality_gate.md` 신설
3) run 상태 기록 스크립트 추가
4) 다음 run 1건 canary 적용
