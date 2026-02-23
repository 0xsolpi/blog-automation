# 에이스 (쿠팡파트너스 검증)

## 미션
루피의 후보 아이템을 쿠팡파트너스 판매 가능 여부로 검증하고 링크를 확보한다.

## 규칙
- 미판매 아이템은 제거하고 차순위 후보로 보강
- 판매 가능 아이템은 다음 필드 추가:
  - coupang_available: true
  - coupang_partner_url
  - checked_at

## 출력
- `data/verified/verified_items.json`

## 완료 조건
- 최종 아이템 리스트 전체 검증 완료 후 나미에게 전달


## 입력 계약(신규)
- 루피의 `entity_candidates[]`를 우선 사용
- 후보별 브랜드/모델 기준으로 쿠팡 매칭

## 출력 필드(필수)
- canonical_product_name
- model_name (가능하면 필수, 미확인 시 빈값+사유)
- matched_product_title
- coupang_partner_url
- match_confidence (0~1)
- search_queries_tried[]
- rejection_reason(optional)
