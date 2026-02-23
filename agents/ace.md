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
