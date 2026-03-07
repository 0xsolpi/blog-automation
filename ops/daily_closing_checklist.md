# 네레 3분 일일 마감 점검표

- 날짜: 
- run_id: 
- 점검자: 네레

## 1) 파이프라인 상태 (목표 40초)
- [ ] 세션-파일 동기화 보정 실행 (`scripts/reconcile_zoro_session_done.py`)
- [ ] run_id 생성/유지 확인
- [ ] 핸드오프 순서 누락 없음 (luffy→ace→nami→zoro→nere→robin→nere)
- [ ] 각 핸드오프 메타 필수값 확인 (`run_id`, `from`, `to`, `generated_at`)
- [ ] `failures` 점검 완료 (사유/재시도 가능 여부/필요 승인사항 기록)

## 2) 품질 게이트 (목표 50초)
- [ ] zoro 판정 명확 (PASS/FIX/HOLD)
- [ ] nere 판정 명확 (✅ 승인 / ⚠️ 조건부 / ❌ 반려)
- [ ] 리스크 레벨 포함 (🟢/🟡/🔴)
- [ ] 자동 반려 조건 위반 없음
  - [ ] 이슈 출처 모호
  - [ ] 클릭베이트 제목
  - [ ] 제품-이슈 연결 부자연
  - [ ] 과도한 광고 톤
  - [ ] 제휴 링크 글 초반 삽입
  - [ ] Admin 쿠팡파트너스 링크 아님

## 3) 링크/수익 안전 (목표 30초)
- [ ] Admin 쿠팡파트너스 링크만 사용
- [ ] 일반 쿠팡 URL/더미 링크 없음

## 4) 업로드 준비성 (목표 40초)
- [ ] `nami_to_zoro` 필수 필드 확인
  - [ ] `category`
  - [ ] `tags` (non-empty)
  - [ ] `image_manifest`
- [ ] `image_manifest` 상세 확인
  - [ ] `featured_image` 지정
  - [ ] `body_images[]` 존재
  - [ ] `placeholder_to_file` 존재
- [ ] 본문 `{{WP_IMAGE_*}}` placeholder 1:1 매핑 완료
- [ ] 이미지 파일명 유니크 규칙 준수 (`run_id-rank-purpose` 권장)

## 5) 보고/승인 트래킹 (목표 20초)
- [ ] Admin 승인 여부/시각 기록
- [ ] robin 업로드 결과 회수 (`URL`, `게시상태`, `실패여부`)
- [ ] nere 최종 보고 전송 완료

---

## 점검 결과 요약
- 총 후보: 
- ✅ 승인 가능: 
- ⚠️ 조건부: 
- ❌ 반려: 
- 최종 상태: (업로드 완료 / 일부 보류 / 전체 보류)
- 특이사항: 
