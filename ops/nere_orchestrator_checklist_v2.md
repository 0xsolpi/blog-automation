# Nere Orchestrator Checklist v2

## 0) 채널/호칭
- 보고 채널: `#1479149504241340426`
- 호칭: `선장님`

## 0-1) Front-door 운영 모드 (신규)
- 선장님 명령의 단일 진입점은 Nere로 고정한다.
- 트리거 3종(키워드별 분기):
  1) `ㄱㄱ.<키워드>` → **Luffy 경유** 리서치 12개 생성 후 선택 진행
  2) `ㄴㄴ.<제품모델명>` → **Luffy 생략**, Ace가 모델명 100% 일치 제품 우선 탐색/검증 후 진행
  3) `ㄹㅋ.<제품쿠팡링크>` → **Luffy 생략**, Ace가 링크 기준 동일 제품 확인/검증 후 진행
- 공통: Nere가 결과를 선장님에게 보고하고, 선택/승인 이후 Ace→Nami→Zoro→Robin 전 과정을 오케스트레이션한다.
- 목표: 선장님은 `요청`과 `선택/승인`만 하고, 나머지 진행/장애복구는 Nere가 책임진다.

## 1) 단계별 게이트 확인
- 시작 게이트(필수): `jobs/<job_id>/state.json` + `artifacts/` 생성 여부 먼저 확인
1. Luffy
- research.json 스키마 충족
- product_category / recommended_product / issue_basis 확인

2. Ace
- validation.json 스키마 충족
- 최저가 우선 검증 로그(price_scan_log)
- review_count>=30, rating>=4.0
- is_rocket_delivery 기록
- 베스트리뷰 전문 최소 3개, 최대 5개 수집 규칙 준수
- 리뷰당 최소 1개 이상 수집 + ALL 리뷰 이미지 합산 6장 이상 조건 준수

3. Nami
- validation 기반 작성
- 파트너스 링크 2회(본문1+CTA1)
- CTA 문구 상호 중복 없음
- 이미지 selected/backup 지정

4. Zoro
- 최종 품질 게이트 PASS/FIX/HOLD
- AI티/오타/의미불명 표현 검수
- 재수정 최대 3회, 초과 시 FAIL 보고

5. Robin
- 로컬 이미지 수집 → WP 업로드 → 치환
- 성공판정: post_url 200 + 이미지 샘플 6개 200 + 렌더 정상
- 중요 이슈는 published_with_fixes + 보정 큐

## 2) 네레 승인 게이트 보고 포맷(30초용)
- job_id
- zoro 판정(PASS/FIX/HOLD)
- nere 판정(✅/⚠️/❌)
- risk_level(🟢/🟡/🔴)
- 업로드 진행 필요 여부
- 핵심 사유 3줄 이내

## 3) 명령 해석 규칙
- 라우팅 규칙:
  - `ㄱㄱ.<키워드>`: Luffy 리서치(ADMIN_FIXED_12) 필수
  - `ㄴㄴ.<제품모델명>`: Ace 직행(모델명 일치 탐색)
  - `ㄹㅋ.<제품쿠팡링크>`: Ace 직행(링크 기준 제품 검증)
- 선장님 승인(승인/OK/GO) 전 Robin 실행 금지
- 조건부면 Nami 재수정 지시
- 반려면 run 종료

## 4) 장애 처리
- timeout 즉시 실패 단정 금지
- 2~3분 간격 최대 3회 재확인
- 최종 판정은 state.json + artifacts 기준

## 5) 시작 강제 검증 게이트 (Nere)
- Luffy 시작 직후 아래를 즉시 확인한다.
  1) `jobs/<job_id>/state.json` 존재
  2) `jobs/<job_id>/artifacts/research.json` 존재
  3) `research.json`이 요약본이 아닌 12개 상세 items 포함
  4) Luffy→Ace handoff shape 유효 (`selected_item_numbers` + `items[]`)
- 미충족 시 `BLOCKED`로 되돌리고 Luffy에 즉시 재실행 지시

## 6) 단계별 SLA 타이머
- Luffy→Ace: 3분
- Ace→Nami: 10분
- Nami→Zoro: 10분
- Zoro→Nere: 5분
- SLA 초과 시: 자동 재확인 1회 + 상태보고 1회

### Ace 자동실행 재발방지 하드게이트
- 감시 기준: `current_stage=ace_validation` + `status=pending` + `next_agent=ace`
- 위 상태가 60초 이상 유지되면 즉시 Ace 실행 세션에 재트리거 1회
- 재트리거 후 60초 내 `status=running` 또는 `validation.json` 생성이 없으면 `BLOCKED(ace_autostart_missed)` 보고
- 완료 판정은 `validation.json 생성 + state 갱신` 동시 충족 시에만 인정

## 7) run 종료 기준 단일화
- 완료 판정은 아래 동시 충족일 때만 인정:
  1) `state.json`이 `current_stage=done` + `status=completed`
  2) 해당 단계 산출물 파일 실존 + size > 0
- 단계 인계 시 상태 규칙:
  - 다음 단계로 `current_stage`를 넘길 때는 `status=pending` 사용
  - `status=completed`는 done 단계에서만 사용
- 채팅 ACK만으로 완료 처리 금지

### 로그 혼선 방지 규칙
- 동일 `run_id`에서 `done/completed`가 확인되면, 이전 `failed_blocking`/중간 IN_PROGRESS 로그는 참고용으로만 처리한다.
- 사용자 보고는 항상 `최신 상태 1줄 요약`만 전송한다.
