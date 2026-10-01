# FINAL_CHECKLIST — 최종 체크리스트

| 항목 | 내용 |
|---|---|
| 문서 | 프로젝트 전체 최종 완료 판단 체크리스트 |
| 주 담당 | D |
| 확인 시점 | Day 4 종료 시 1차, Day 5 제출 전 최종 |
| 관련 문서 | [PRD.md](PRD.md), [TECH_SPEC.md](TECH_SPEC.md), [WORK_UNITS.md](WORK_UNITS.md) |

**판정 기준:** 아래 **P0 (필수)** 항목이 모두 체크되어야 프로젝트 완료로 본다. **P1** 은 권장 항목이다.

**D 검증 기준(2026-10-01):** main `657d7ce` + D 문서 갱신본(실행 코드는 당시 main과 동일) 비유료533/유료 opt-in10개 제외, frontend build/lint 통과. 유료40문항·인사이트9개·라우트7개는29a90ea 과거 기록이며 합산하지 않는다. #34는 고정 인사로 보완·병합됐다. 9/30ffe31fb 배포의CSV/Excel·모바일·null 표시와 AI 상태 모의 UI를 확인했다. #42be35ce4 모드 전환·분석 스냅샷·null 사유·분석 중 질문 차단·이전 응답 폐기/새pending 보존을 재검증해 D 승인했다. #42는d295f3a로, #37은A 승인 후3b5bc89로 병합됐다. 최신 main 실행 코드는be35ce4와 동일하다. B는10/1a57eb1b까지 Live 확인을 회신했다. 최신 배포/팀 최종 승인은 별도이며 다른 담당자 체크는 임의 변경하지 않는다. 상세: `D_WEDNESDAY_STATUS.md`.

**10/1 저녁 갱신 (C):** 배포 화면·저장소 기록(`gh`, `git log`, `git grep`)으로 사실을 대조해 체크를 갱신했다. 지키지 못했거나 확인하지 못한 항목은 체크하지 않고 사유를 적었다. 최종 승인 표는 각자 직접 서명한다.

---

## 1. 작업 완료 (P0)

- [ ] WORK_UNITS 의 모든 작업(WU-*)의 완료 조건이 체크됨 — ⏳ 10/1 저녁 기준 7개 미체크 — 팀 결정·권한이 필요한 항목이며 사유는 WORK_UNITS 에 적음
- [ ] 열려 있는 PR 없음 (모두 Merge 또는 Close) — ⏳ #53(쿠팡 판매 분석)은 발표 후 머지, #39(발표 자료 초안)는 발표 후 닫기 예정
- [x] 치명적(시연 불가) 버그 Issue 0건 — 열린 이슈 0건 (10/1 `gh issue list`)

## 2. 핵심 기능 (P0)

### 파일 업로드
- [x] 여러 Excel/CSV 파일 동시 업로드 — WU-FE-01, 10/1 배포 화면 시연 ①(CSV 4개 동시)
- [x] 업로드 파일 목록에 파일명·플랫폼·기간 표시 — WU-FE-03, 10/1 배포 화면
- [x] 데이터 미리보기 표시 — `/api/preview` 최대 10행 (WU-BE-03), 10/1 배포 화면

### 데이터 처리
- [x] 쿠팡 데이터가 공통 구조로 정규화됨 — WU-DA-02, `test_normalize*`·`test_analysis.py`
- [x] 네이버 데이터가 공통 구조로 정규화됨 — WU-DA-02, `test_normalize*`·`test_analysis.py`
- [x] 공통 구조 9개 필드(`period, platform, product_id, product_name, revenue, orders, units, ad_spend, ad_revenue`)가 계약과 일치 — `test_normalize_files_schema_and_dtypes`

### KPI · 비교
- [x] 매출·주문·판매량·광고비·광고매출·ROAS 표시 — 간단보기는 매출액·광고비·ROAS, 자세히보기에서 주문·판매량·광고매출 (10/1 배포 화면, A.md)
- [x] ROAS = 광고 전환매출 ÷ 광고비 × 100 으로 계산 — WU-DA-03 `kpi.py` — 쿠팡 3,500,000 ÷ 1,200,000 = 291.7% (10/1 배포 화면)
- [x] 전월 대비 증감률(%) 및 ROAS 증감(%p) 표시 — 10/1 배포 화면: 쿠팡 매출 +21.2%, ROAS −19.4%p
- [x] 플랫폼 비교(쿠팡 vs 네이버) 표시 — 쿠팡·네이버 카드 (10/1 배포 화면), `PlatformCompare.tsx` (WU-FE-04)
- [x] 매출·ROAS 추이 차트 표시 — `TrendChart.tsx` (WU-FE-04), 자세히보기 월별 추이 (A.md)
- [x] 이상 신호 표시 (P1) — 배지 '광고비 +28.0% 증가, ROAS −14.2%p' (10/1 배포 화면)

### AI
- [x] 자연어 질문 → 분석 계획 JSON → pandas 계산 → 결과 표시 — 시연 ② 10/1 배포 화면, 고정 질문 40/40 (WU-AI-02)
- [x] AI 인사이트가 근거 / 확인 항목 / 행동 제안(/ 한계)으로 분리 표시 — WU-AI-03·FE-05, 10/1 배포 화면
- [x] 분석 불가 질문에 안내 메시지 표시 — `unsupported_question` (WU-AI-02·FE-05, 미지원 14문항)

## 3. 계산 정확성 (P0)

- [x] fixture 입력 시 결과가 `expected_kpis.json` 과 100% 일치 (#35 근거 + D 로컬 정답4덩어리 독립 재현)
- [x] 검증 예시 일치: 매출 **+21.2%**, 광고비 **+28.0%**, ROAS **326.7% → 312.5% (−14.2%p)**
- [x] 같은 입력으로 여러 번 실행해도 KPI 동일 (D 10회 반복/역순 업로드 재현)
- [x] 분모 0(광고비 0, 전월 값 0)에서 오류·무한대 없이 `-` 표시 — 실제 API null/HTTP200, 9/30 ffe31fb 배포 및10/1 #42 로컬 직접 확인; #42의 null 사유 툴팁 문구는 별도 비블로킹 보완
- [x] 데이터가 한 달뿐일 때 비교 항목이 오류 없이 비어 있음 (previous_period/previous=null, change는 객체·각 값null)

## 4. AI 품질 (P0)

- [x] AI 응답의 사실 문장은 검증된 계산 결과에서 생성 (검증 시나리오 숫자 변조 0건; main 회귀 + 동일 AI 구현의 실제 fixture API 기록)
- [x] 데이터에 없는 요인(광고 소재, CTR, CPC, CVR, 경쟁사 가격, 시장 상황)을 원인으로 **단정한 응답 0건** (검증 시나리오 기준; 자유 원인 문장 생성 경로 제거)
- [x] 확인할 수 없는 범위와 필요한 추가 데이터를 서버의 `limitations`에 표시
- [x] 원인은 확정하지 않고, 입력 신호에 근거한 점검·행동 후보만 허용
- [x] 질문 해석 테스트 세트 정확도 90% 이상 (동일 AI 구현의 실제 `gpt-6-luna` 고정 40/40 기록; 일반 정확도 보장 아님)
- [x] LLM 실패 상태에서 KPI·차트는 정상 표시되고 AI 영역만 오류 안내 — 서버/API 회귀, 9/30 ffe31fb 배포의 AI 상태만 모의한 오류 UI, 10/1 #42 로컬 실제 키 없음 오류로 확인. 실제 공급자 장애 유발 시험·최신 수정본 배포 확인은 별도

## 5. 오류 처리 (P0)

각 케이스에서 서버가 올바른 오류 코드를 반환하고, 화면에 이해 가능한 메시지가 표시되는지 확인.

| 케이스 | API 오류 코드 | 서버 | 화면 |
|---|---|---|---|
| 빈 파일 | `EMPTY_FILE` | [x] | [x] |
| 필수 컬럼 누락 | `MISSING_COLUMNS` | [x] | [x] |
| 잘못된 숫자 | `INVALID_NUMBER` | [x] | [x] |
| 파일 크기 초과 | `FILE_TOO_LARGE` | [x] | [x] |
| 파일 개수 초과 | `TOO_MANY_FILES` | [x] | [x] |
| 미지원 확장자 | `UNSUPPORTED_FILE_TYPE` | [x] | [x] |
| 미지원 플랫폼 | `UNKNOWN_PLATFORM` | [x] | [x] |
| 질문 길이 초과 | `QUESTION_TOO_LONG` | [x] | [x] |
| 잘못된 질문 | `insight.status = unsupported_question` | [x] | [x] |
| LLM 장애 | `insight.status = llm_error` | [x] | [x] |

근거: 서버 열 = `TEST_RESULTS.md` 2장(로컬 pytest·배포 서버)과 API 테스트, 화면 열 = `TEST_RESULTS.md` 3장(9/30 배포 화면)과 WU-FE-05. `QUESTION_TOO_LONG` 은 입력창이 300자로 제한되고(WU-FE-05) 서버 테스트가 있다. `llm_error` 화면은 AI 상태를 모의한 시험이며 실제 공급자 장애·키 제거 시험은 하지 않았다.

- [x] 서버 오류 응답에 스택트레이스가 노출되지 않음 — WU-BE-05 (`INTERNAL_ERROR`, 스택트레이스 응답 노출 금지)

## 6. UX (P0 / P1)

- [x] 업로드·분석·AI 응답 중 로딩 표시 (P0) — WU-FE-06
- [x] 요청 중 중복 클릭 방지 (P0) — WU-FE-06 (버튼 `disabled`)
- [x] 금액·비율·%p 포맷 일관 (P0) — WU-FE-02 `lib/format.ts`
- [x] 증가/감소 색상 구분 (P0) — WU-FE-02
- [x] 모바일 폭(375px)에서 주요 화면 확인 가능 (P1) — 10/1 배포 화면 375×812 에뮬레이션, 가로 스크롤 없음·콘솔 오류 0건 (실제 기기는 미확인, WORK_UNITS FE-06)
- [x] 브라우저 콘솔 에러 없음 (P1) — 10/1 새 화면(#55) 기준 앱 콘솔 오류 없음 (A.md, WU-FE-06)

## 7. 테스트 (P0)

- [x] main657d7ce + D 문서 갱신본(실행 코드 동일) 비유료533 passed/10 deselected(21.38초), 10/1 직접 재실행; 이전 실행 수와 합산하지 않음
- [x] Frontend production build·타입 검사·lint 성공 (10/1, main657d7ce 실행 코드와 동일한 D 문서 갱신본; #42 c7367af도 별도로 통과)
- [x] C+D 테스트 결과/활용 사례 main 반영 — #20/#26/#18/#22/#35 완료; 이번 완료 근거 문서 후속은 A 리뷰 대상

## 8. 배포 · 보안 (P0)

- [x] Backend Render 배포 URL `/health` → `{"status":"ok"}` (9월 30일 HTTP 200) — 10/1 저녁 HTTP 200 `{"status":"ok"}` 재확인
- [x] Frontend Vercel 배포 URL 접속 가능 (9월 30일 기존 배포 화면) — 10/1 저녁 HTTP 200 재확인
- [x] 배포된 Frontend → Backend 호출 시 CORS 오류 없음 (공개 fixture preview/analyze HTTP 200; 새 개선본 배포는 별도) — 10/1 시연 ①~④ 배포 화면에서 CORS 오류 없이 동작
- [x] 배포 환경에서 전체 흐름(업로드 → KPI → 차트 → 질문 → 인사이트) 성공 — 10/1 12:30 팀 시연 ①~④ 확인 + 오후 새 화면 재확인
- [x] LLM API 키가 저장소·커밋 히스토리·프론트 번들·로그 어디에도 노출되지 않음 — 전체 커밋 기록에서 키 패턴 0건 (10/1 `git grep`), 프론트 번들·로그는 WU-BE-06(9/30) 확인
- [x] `.env` 파일이 커밋되지 않았고 `.env.example` 만 존재 — 추적 파일은 `backend/.env.example`·`frontend/.env.example` 뿐 (10/1 `git ls-files`)
- [x] 업로드 데이터가 서버에 저장되지 않음 — `core/uploads.py` 가 메모리로만 처리 (B.md 코드 확인)
- [x] 시연 직전 Render 워밍업(`/health` 호출) 계획 있음 — 발표 30분 전 `/health` 호출 (대본·시연 체크리스트)

## 9. 협업 규칙 준수 (P0)

- [ ] `main` 직접 Push 없음 (모든 변경이 PR 을 통해 Merge) — ⏳ 지키지 못함 — PR 없이 main 에 들어간 커밋 10개 (초기 커밋·개발 문서 2, README 1, 스마트스토어 2, 10/1 화면 작업 5; `git log origin/main --first-parent`)
- [ ] 모든 PR 이 작성자 외 1명 이상 리뷰·승인 (A→B, B→C, C→D, D→A) — ⏳ 머지 PR 46개 중 31개만 타인 승인 (10/1 `gh pr list`). 자기 PR 을 자기가 승인한 경우는 0
- [x] 4명 모두 구현 코드 PR 을 Merge 한 이력이 있음 — A·B·C·D 모두 구현 PR 머지 (타인 승인 PR: A 6, B 11, C 10, D 4)
- [ ] `shared/contracts/` 변경이 전원 합의 후 반영됨 — ⏳ WU-COM-01 참고 — 4명 전원이 승인한 계약 PR 없음 (작성자 + 3명 동의 원칙은 #20·#28 에서 적용)
- [x] 최신 `main` 에서 전체 흐름 동작 확인 — main `9afd917` 배포 Live (B, Render Events) + 시연 ①~④ 10/1 오후

## 10. 문서 (P0)

- [ ] `README.md` — 서비스 소개, 배포 URL, 실행 방법, 스크린샷, 팀 구성 — ⏳ 스크린샷 없음 (서비스 소개·배포 URL·실행 방법·팀 구성은 있음)
- [x] `DevelopDoc/PRD.md` — 실제 구현 범위와 일치 — 10/1 `11. 구현 반영` 섹션 추가 (실제 내보내기 4종·월 직접 입력·상품 진단·새 대시보드)
- [x] `DevelopDoc/TECH_SPEC.md` — 실제 API·스키마와 일치 — API·스키마는 계약 예시 JSON 과 `test_api.py` 로 대조, 10/1 8-4(상품 진단)·9장(새 화면) 반영
- [x] `DevelopDoc/WORK_UNITS.md` — 체크 상태 최신화 — 10/1 저녁 갱신 (미체크 7개는 사유 기재)
- [x] `DevelopDoc/FINAL_CHECKLIST.md` — 본 문서 전 항목 확인 — 10/1 저녁 사실 대조 후 갱신 (미체크는 사유 기재)
- [x] 테스트 결과 문서 (C + D) — `TEST_RESULTS.md` (C 1~5장, D 6장)
- [x] 역할 분담 / 일정 문서 (A) — `Seller_Insight_4person_Roles_and_Collaboration.md` (역할·5일 작업 순서)
- [x] AI 활용 사례 문서 (D) main 반영 — `AI_USAGE_CASES.md` 대표 사례3개, #22 A 승인·병합 완료

## 11. 발표 · 제출 (P0)

- [x] 발표 자료 완성 (문제 → 해결 → 데모 → 아키텍처 → AI 신뢰성 → 역할 분담) — `docs/presentation` 브랜치(#39)의 덱 20장 (역할 분담·개발 일정 포함)
- [x] 시연 시나리오 작성 및 리허설 1회 이상 — 10/1 리허설 2회 (25분, 17분)
- [x] 시연용 fixture 파일 준비 — `shared/fixtures/` 정상·실패·exports
- [x] 배포 장애 대비 백업(로컬 실행 또는 시연 녹화) 준비 — 시연 화면 녹화 완료 (C, 10/1 저녁)
- [ ] 최종 버전 태그 `v1.0.0` 생성 — ⏳ 제출 직전 생성 예정
- [ ] 제출 완료

---

## 최종 승인

| 역할 | 담당 영역 확인 | 확인자 | 일시 |
|---|---|---|---|
| A | Frontend / UI | | |
| B | Backend / API / 배포 | | |
| C | Data / KPI 정확성 | | |
| D | AI 품질 / 최종 체크리스트 | | |
