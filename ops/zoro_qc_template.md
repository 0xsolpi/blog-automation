# ZORO QC REPORT 템플릿 (표준 고정안)

```md
[ZORO_QC_REPORT]

run_id: <필수>
from: nami
to: nere
generated_at: <KST ISO8601>

post_id: <필수>
title: <필수>
source: <초안 파일/링크>

risk_level: <LOW|MID|HIGH>
final_profitability_score: <0.0~10.0>

verdict: <PASS|FIX|HOLD>

summary:
- 한줄 총평

checks:
  basic:
    typo: <PASS|FIX>
    spelling_grammar: <PASS|FIX>
  context:
    flow_consistency: <PASS|FIX>
    duplication_hype: <PASS|FIX>
  policy:
    medical_claim: <PASS|FIX|HOLD>
    income_guarantee: <PASS|FIX|HOLD>
    celebrity_false_assoc: <PASS|FIX|HOLD>
    clickbait_exaggeration: <PASS|FIX|HOLD>
    coupang_link_early: <PASS|FIX|HOLD>
  seo:
    h2_count_3plus: <PASS|FIX>
    title_has_source: <PASS|FIX>
    intro_5to7_lines_context: <PASS|FIX>
    product_name_first_paragraph: <PASS|FIX>
  conversion:
    affiliate_after_explaining: <PASS|FIX>
    recommended_for_section: <PASS|FIX>
    pre_purchase_check_section: <PASS|FIX>
    aggressive_cta_absent: <PASS|FIX>
  image_integrity:
    relative_path_absent: <PASS|FIX|HOLD>
    placeholder_absent_or_mapped: <PASS|FIX|HOLD>
    fabricated_url_absent: <PASS|FIX|HOLD>
    allowed_domain_only: <PASS|FIX|HOLD>
    sample_http_200_3plus: <PASS|FIX|HOLD>

annotations:
- <!-- Zoro: 과장 표현 완화 -->
- <!-- Zoro: 정책 리스크 문구 제거 -->

fix_requests:
- [ ] 수정 필요 항목 1
- [ ] 수정 필요 항목 2

hold_reason:
- <HOLD일 때 필수, 발행 금지 사유 명확히>

failure_tracking:
  repeated_reason_count: <숫자>
  action: <continue|stop_and_report_to_nere>
  note: <동일 사유 3회 이상이면 stop_and_report_to_nere>

handoff_rule:
- PASS만 nere 업로드 가능 여부 확인 단계로 전달
- FIX/HOLD는 nami 재수정 루프
```

## 운영 규칙 요약
- PASS: 네레 전달 (단, image_integrity 5개 전부 PASS일 때만)
- FIX: 수정요청 + 체크 항목 지정
- HOLD: 발행 금지 사유 명시 + 즉시 네레 보고
- 동일 사유 3회 이상 FIX/HOLD: 중단 후 네레 보고

## 이미지 URL 강제 규칙 (조로 게이트)
- URL 패턴 추정/문자열 조합(`.../wp-content/uploads/...` 수동 생성) 금지
- 나미 산출물은 아래 중 하나만 허용:
  1) `{{WP_IMAGE_*}}` placeholder + `placeholder_to_file` 완전 매핑
  2) 실제 업로드 검증된 URL(샘플 3개 이상 HTTP 200 증거 포함)
- 위반 시 PASS 금지(HOLD)
