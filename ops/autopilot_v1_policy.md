# Autopilot v1 Policy

## Human Touchpoints (only 2)
1) 리서치 요청
2) 아이템 선택

선택 이후에는 포스팅 업로드 완료까지 전 구간 자동화.

## Pipeline
Luffy -> Ace -> Nami <-> Zoro (fix loop up to 3) -> Nere Upload -> Admin notify

## Rules
- 중간 ACK/announce를 사용자 채널로 보내지 않는다.
- 단계 실패 시 내부 재시도 최대 3회.
- 3회 실패 시 BLOCKED 1회만 보고.
- 업로드 전 필수 검사:
  - placeholder 0
  - `.md`/`../` 링크 0
  - 이미지 렌더 OK
  - 제휴 고지문 존재

## Robin
- 별도 역할 부여 전까지 파이프라인 비활성(Idle).
