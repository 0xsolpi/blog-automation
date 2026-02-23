# Luffy Quality Checklist (고정 기준)

## 1) 노이즈 차단
- 언론사/정치/플랫폼명 토큰 제거
- 순위/요약형 제목(Top10, 총정리, 브리프) 제거

## 2) 모델명 유효성
- brand+model 모두 존재해야 함
- 모델은 alpha+digit 혼합 또는 뷰티 규칙(예: SPF50, 21N1)
- 시즌코드/플랫폼명/브랜드명-only 금지

## 3) 근거 링크/요약
- evidence_links 최소 1개
- evidence_briefs 최소 2개 권장(미만 시 저신뢰)
- issue_reason은 출처 맥락 포함

## 4) 품질 게이트
- score >= 60 우선
- influencer/news/blog 언급 있는 항목 우선 정렬
- 품질 미달이면 개수 줄여서라도 배출

## 5) 일일 점검 지표
- noise_leak_count
- valid_model_rate
- evidence_coverage_rate
- influencer_priority_rate
