# Handoff Contract v2 (State/Artifact-first)

## 원칙
- 대화 기반 인계 금지. **상태 + 산출물** 기준으로만 인계한다.
- 모든 단계는 `job_id`를 필수로 포함한다.
- 완료 판단은 메시지가 아니라 산출물 검증으로 한다.

## 필수 인계 필드
- `job_id`
- `stage`
- `input`
- `output`
- `status`
- `retry_count`
- `next_agent`
- `blocking_reason`
- `artifacts_path`

## 표준 경로
- `jobs/<job_id>/state.json`
- `jobs/<job_id>/artifacts/research.json`
- `jobs/<job_id>/artifacts/validation.json`
- `jobs/<job_id>/artifacts/draft.md`
- `jobs/<job_id>/artifacts/final.md`
- `jobs/<job_id>/artifacts/publish.json`

## 상태값 의미(고정)
- `current_stage`: 지금 처리해야 할 단계
- `status=pending`: 해당 단계 시작 대기(이전 단계가 넘긴 직후)
- `status=running`: 해당 단계가 실제 처리 중
- `status=completed`: 파이프라인 최종 완료(`current_stage=done`)에만 사용
- 금지: 다음 단계로 stage를 넘기면서 `status=completed`를 함께 쓰는 것

## 단계별 완료 게이트
1) Luffy 완료 조건
- `research.json` 존재
- `state.current_stage=ace_validation`
- `state.status=pending` (다음 단계 대기 상태)
- `state.next_agent=ace`
- `research.json`은 `ops/luffy_research_schema_v2.json`을 충족
  - `product_category` 필수
  - `recommended_product`는 Ace의 쿠팡 검색 가능한 구체 상품명으로 작성
  - `issue_basis`는 Robin 작성 참고 가능한 상세 근거로 작성

2) Ace 완료 조건
- `validation.json` 존재
- `state.current_stage=nami_draft`
- `state.status=pending` (다음 단계 대기 상태)
- `eligible_products.length >= 1`
- `affiliate_rule_check=pass`
- `next_agent=nami`
- `best_reviews` 3개 전문 + 이미지 정책 충족 확인
- `coupang_partner_link` 유효 링크(`https://link.coupang.com/...`) 확인

2-1) Ace 실패 조건(강제)
- 아래 중 하나라도 미충족이면 Ace는 Nami로 인계 금지:
  - `affiliate_rule_check!=pass`
  - `eligible_products.length < 1`
  - 리뷰/이미지 하드게이트 미충족
  - 파트너스 링크 하드게이트 미충족
  - `partner_link_generated` 체크리스트 미기록 또는 fail
- 실패 시 상태 고정:
  - `current_stage=ace_validation`
  - `status=failed_blocking`
  - `next_agent=nere`
- `validation.json`은 `ops/ace_validation_schema_v2.json`을 충족
  - `checklist[]` 필수 (최소 4개)
  - 체크리스트 필수 항목 권장 ID:
    - `format_integrity`
    - `searchability_for_coupang`
    - `policy_risk`
    - `commercial_intent`
    - `coupang_existence`
    - `coupang_partner_link`
    - `review_quality_threshold`
    - `review_assets_collected`
- Ace 핵심 책임(고정):
  1) 루피 선정 아이템의 쿠팡 판매 존재 검증
  2) 판매중인 아이템의 쿠팡 파트너스 링크 생성/확보(Admin API 사용)
  3) 대표 제품 이미지 확보
  4) 베스트 리뷰 3개 전체 내용 + 리뷰당 이미지 최대 3개 확보
  5) 리뷰 이미지 수집 시 사람/얼굴 감지 이미지 제외(`usable=false`) 후 다음 이미지로 대체
- 선정 통과 기준:
  - **최저가 상품부터 우선 검증**
  - `review_count >= 30`
  - `rating >= 4.0`
- 검증 순서 규칙:
  1) 동일 키워드 검색 결과를 가격 오름차순으로 정렬
  2) 최저가 상품부터 `review_count/rating` 기준 검증
  3) 기준 미충족 시 다음 최저가 상품으로 순차 이동
  4) 기준 충족 상품 발견 즉시 `selected_for_nami` 후보로 확정
  5) 선정/검증한 상품의 `로켓배송 가능 여부(is_rocket_delivery)`를 `validation.json`에 함께 기록
- 쿠팡 미존재 시 즉시 `Fail` 처리 (`fail_code=COUPANG_NOT_FOUND`)
- 검색 결과는 `price_scan_log`(가격/평점/리뷰수/탈락사유)를 `validation.json`에 남긴다.
- 리뷰 이미지 예외 처리(고정):
  - 한 리뷰에서 사람/얼굴 제외 후 이미지가 3개 미만이면 `2개까지 허용`
  - `1개 이하`만 확보되면 해당 리뷰는 `Fail` 처리 후 다음 베스트 리뷰로 재수집
  - 리뷰 이미지 수집 `Fail`이 3회 이상 누적되면 해당 아이템은 최종 `Fail` 처리
  - 최종 Fail 시 `#1479149504241340426` 채널에 Fail 보고를 필수 전송

3) Nami 완료 조건
- `draft.md` 존재
- `state.current_stage=zoro_review`
- `state.status=pending` (다음 단계 대기 상태)
- `next_agent=zoro`

4) Zoro 완료 조건
- `final.md` 존재
- `status in [completed, waiting_admin]`
- `next_agent=admin`

5) Robin 완료 조건
- `publish.json` 존재
- `post_url` + `post_id` + `posted_at` 존재
- `status=completed`
- `next_agent=none`

## 실패 상태 표준
- `failed_retryable`: 자동 재시도 대상
- `failed_blocking`: 수동 개입 필요
- `waiting_admin`: 선장님 승인 대기

## 멱등성 규칙
- 동일 `job_id` 재실행 시 기존 completed 산출물 있으면 재생성 금지
- 게시 단계에서 `post_id` 또는 `post_url` 존재 시 중복 업로드 금지
- 링크/치환 작업은 "없을 때만 삽입" 규칙 적용

## 오케스트레이션 규칙
- 모든 인계는 네레 중재 고정:
  - `agent -> nere -> next_agent`
- 보고 채널: `#1479149504241340426`
- 핸드오프 호출 시 다음 에이전트 멘션 필수

### Ace 실행 세션 단일화(강제)
- Ace 실행 주체 세션은 `agent:ace:discord:channel:1479149504241340426` 단일로 고정한다.
- 개인/보조 Ace 세션은 실행 트리거를 처리하지 않는다(상태조회/대화 전용).
