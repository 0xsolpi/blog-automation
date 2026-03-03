# ACE 자동검증 트리거 누락 방지 정책 (필수)

적용 대상: 에이스의 루피 handoff 처리 전체

## 1) 상태머신 강제
반드시 아래 상태만 사용:
- `RECEIVED`
- `QUEUED`
- `RUNNING` (기존 STARTED 대체)
- `DONE` 또는 `BLOCKED`

금지:
- enqueue/실행 확인 전 `RUNNING(STARTED)` 송신

## 2) STARTED 허위양성 방지
- 검증 작업 enqueue 성공 + 실행 진입 로그 확인 전에는 시작 상태를 보내지 않는다.
- 시작 메시지는 실제 실행 스레드/함수 진입 시점 1회만 보낸다.

## 3) 워치독(필수)
- `RECEIVED` 후 120초 내 `RUNNING` 미도달 시:
  1) 자동 재큐잉 1회
  2) 즉시 `IN_PROGRESS reason=trigger_recovery` 보고
  3) 재큐잉도 실패하면 `BLOCKED` 보고

## 4) idempotency 키 고정
- 키: `<run_id>:<selected_numbers_sorted>:ace_validation`
- 동일 키 재수신 시:
  - RUNNING/DONE 상태면 중복 실행 금지
  - RECEIVED/QUEUED에 정체면 복구 루틴(재큐잉) 수행

## 5) 완료 조건 강화
`DONE_NOTIFY` 전송 성공 전에는 DONE 금지.
완료 보고 필수 포맷:
`DONE run_id=... selected=... path=... validated=... failures=...`

## 6) 관측성
- 각 단계 타임스탬프 기록:
  - received_at / queued_at / running_at / done_at
- 지연 원인은 enum으로 기록:
  - `trigger_missing`
  - `queue_timeout`
  - `external_tool_blocked`
  - `validation_error`
