# Job Bootstrap v2 (Pilot-style)

목적: 모든 run을 `blog-automation/jobs/<job_id>/` 기준으로 시작/진행한다.

## 시작 순서 (고정)
1. Luffy가 `job_id`를 먼저 발급한다.
2. 아래 경로를 생성한다.
   - `jobs/<job_id>/state.json`
   - `jobs/<job_id>/artifacts/`
3. state 초기값(최소)
   - `job_id`
   - `current_stage=luffy_research`
   - `status=running`
   - `next_agent=luffy`
   - `artifacts.research|validation|draft|final|publish` 절대경로
4. 이후 모든 에이전트는 자신의 단계 산출물을 `jobs/<job_id>/artifacts/*`에만 쓴다.
5. 단계 완료 시 `state.json`의 `current_stage/status/next_agent/updated_at`를 갱신한다.

## 공통 원칙
- 레거시 handoff 경로(`agents/*/data/handoff/...`)는 보관/로그 용도로만 허용한다.
- 운영 완료 판정은 `jobs/<job_id>/state.json + artifacts/*` 기준으로만 한다.
- 상태/산출물 불일치 시 최신 `state.json`을 단일 진실소스로 본다.
