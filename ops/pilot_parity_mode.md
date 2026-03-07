# PILOT_PARITY_MODE (강제)

목표: 모든 에이전트가 `2026-03-06-2135-pipeline-v2-pilot-001`과 동일한 상태/산출물 흐름으로 실행한다.

## 공통 강제 규칙
1. 단일 진실소스: `/home/solpi/work/blog-automation/jobs/<job_id>/`
2. 필수 파일:
   - `state.json`
   - `artifacts/research.json`
   - `artifacts/validation.json`
   - `artifacts/draft.md`
   - `artifacts/final.md`
   - `artifacts/publish.json`
3. 각 단계 완료 시 `state.json`의 `current_stage/status/next_agent/updated_at`를 즉시 갱신한다.
4. 레거시 경로(`agents/*/data/handoff/*`)는 로그/백업 전용이며, 완료 판정에 사용하지 않는다.

## 단계별 출력 고정
- Luffy: `artifacts/research.json`에 12개 상세 items(요약만 저장 금지), 완료 후 `ace_validation/pending/ace`
- Ace: `artifacts/validation.json`, 완료 후 `nami_draft/pending/nami`
- Nami: `artifacts/draft.md`, 완료 후 `zoro_review/pending/zoro`
- Zoro: `artifacts/final.md` + 판정, PASS면 `admin_approval/waiting_admin/admin`, FIX/HOLD면 규칙대로
- Robin: `artifacts/publish.json`, 완료 후 `done/completed/none`

## 보고 채널
- `#1479149504241340426` 고정
