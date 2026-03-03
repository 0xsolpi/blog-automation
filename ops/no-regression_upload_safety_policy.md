# No-Regression Upload Safety Policy (Mandatory)

## 목적
업로드 정체/무응답/실행 누락 재발을 운영적으로 차단한다.

## 강제 규칙
1) 업로드 시작 시 `STARTED` 이벤트 즉시 기록
2) 2분 내 상태 변경(`IN_PROGRESS`) 없으면 Watchdog 경고 + 자동 재시도
3) 업로드 시작 후 5분 내 `DONE(url, published_at)` 없으면 자동 실패 처리
4) 실패 2회 시 즉시 `BLOCKED` 전환 + 백업 경로(대체 워커) 자동 실행
5) 완료 보고 필수 3항목:
   - `post_url`
   - `published_at`
   - `render_check` (OK/FAIL)
   (하나라도 없으면 미완료로 간주)
6) 중간 상태 문구(예: 준비중/진행중)만 있고 URL 없으면 완료 인정 금지
7) 업로드 워커는 단일 탭만 사용, 완료 즉시 탭 정리(`tabs_cleanup: done`)

## 자동 분기
- 기본: 네레 업로드 워커
- 백업: 로빈(예외적 강제 투입)
- 네레 5분 SLA 위반 시 백업 경로 자동 승격

## 품질 게이트(발행 전)
- placeholder 0
- `.md`/`../` 링크 0
- 이미지 렌더 OK
- 제휴 고지문 원문 일치

## 재발 판정
아래 중 하나라도 발생하면 재발로 기록:
- STARTED 후 5분 초과 무결과
- URL 없이 완료 보고
- 탭 미정리 반복
