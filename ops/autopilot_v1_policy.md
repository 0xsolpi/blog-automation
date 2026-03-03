# Autopilot v1 Policy

## Human Touchpoints (only 2)
1) 리서치 요청
2) 아이템 선택

선택 이후에는 포스팅 업로드 완료까지 전 구간 자동화.

## Pipeline
Luffy -> Ace -> Nami <-> Zoro (fix loop up to 3) -> Robin Upload -> Nere Final Notify

## Rules
- 중간 ACK/announce를 사용자 채널로 보내지 않는다.
- 단계 실패 시 내부 재시도 최대 3회.
- 3회 실패 시 BLOCKED 1회만 보고.
- 업로드 전 필수 검사:
  - placeholder 0
  - `.md`/`../` 링크 0
  - 이미지 렌더 OK
  - 제휴 고지문 존재

## Robin (Primary Uploader)
- 역할: 조로 PASS 이후 워드프레스 업로드 전담 실행자
- 필수 규칙:
  1) STARTED -> IN_PROGRESS -> DONE 이벤트 누락 금지
  2) 업로드 시작 후 5분 내 결과 미보고 시 자동 BLOCKED
  3) 완료 보고 필수: post_url, published_at, render_check, tabs_cleanup
  4) 단일 탭 실행 + 완료 즉시 탭 정리(`tabs_cleanup: done`)
  5) 품질 게이트(placeholder 0 / .md,../ 링크 0 / 이미지 렌더 OK / 제휴고지문 원문 일치) 미충족 시 발행 금지
- Nere는 감시/재시도 오케스트레이션 담당, 결과만 사장님에게 보고
