# 네레 → 루피 지시 템플릿 (포맷 일치 강제)

아래 형식으로만 지시한다.

```text
[admin_command]
run_id: <run_id>
from: admin
to: luffy
format_lock: ADMIN_FIXED_12
command: <리서치 요청>
requirements:
- 선장님 합의 보고 양식(12개 고정: 1~3 네이버 / 4~6 froogle / 7~9 youtube / 10~12 뉴스)으로만 회신
- 각 아이템 번호(1..12) + 이슈 근거 + 지표 + 리스크 포함
- 마지막 줄에: "선택 번호를 알려주세요(예: 2,3)"
- Admin 선택(3단계) 전 에이스 전달 금지
forbidden:
- 임시 요약/축약 포맷
- 섹션 누락
- 번호 체계 변경
```

## 검증
- 루피 회신이 `format_lock: ADMIN_FIXED_12`를 포함하지 않거나
  12개 구조가 아니면 네레가 즉시 재요청한다.
