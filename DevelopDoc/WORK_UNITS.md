# WORK_UNITS — 단위 작업 명세

| 항목 | 내용 |
|---|---|
| 문서 | 단위 작업 명세 및 작업별 완료 조건 |
| 정리 | B (각 담당자가 자기 작업 작성) |
| 관련 문서 | [PRD.md](PRD.md), [TECH_SPEC.md](TECH_SPEC.md), [FINAL_CHECKLIST.md](FINAL_CHECKLIST.md) |

**사용법**
- 작업 ID 형식: `WU-<영역>-<번호>` (COM=공통, FE=A, BE=B, DA=C, AI=D, INT=통합)
- 모든 완료 조건이 체크되어야 해당 작업을 완료로 본다.
- PR 설명에 작업 ID를 적고, Merge 시 체크박스를 갱신한다.

## 작업 요약

| ID | 작업 | 담당 | 리뷰 | Day | 선행 |
|---|---|---|---|---|---|
| WU-COM-01 | 공통 데이터 구조 · API 계약 확정 | 전원 (B 정리) | 전원 | 1 | — |
| WU-COM-02 | 저장소 · 협업 환경 구성 | B | A | 1 | — |
| WU-COM-03 | 프로젝트 뼈대 생성 | A, B | C | 1 | COM-02 |
| WU-DA-01 | 테스트 fixture 제작 | C | D | 1–2 | COM-01 |
| WU-FE-01 | 파일 업로드 UI | A | B | 2 | COM-03 |
| WU-FE-02 | KPI 대시보드 UI | A | B | 2 | COM-01 |
| WU-BE-01 | FastAPI 서버 · 설정 · CORS | B | C | 2 | COM-03 |
| WU-BE-02 | Pydantic 스키마 | B | C | 2 | COM-01 |
| WU-BE-03 | 파일 업로드 검증 · `/api/preview` | B | C | 2 | BE-01, DA-02 |
| WU-DA-02 | 플랫폼 데이터 정규화 | C | D | 2 | DA-01 |
| WU-DA-03 | KPI 계산 | C | D | 2 | DA-02 |
| WU-AI-01 | LLM 클라이언트 · 실패 처리 | D | A | 2 | COM-03 |
| WU-AI-02 | 질문 → 분석 계획 JSON (Planner) | D | A | 2 | AI-01 |
| WU-DA-04 | 전월 · 플랫폼 비교 / 계획 실행 | C | D | 3 | DA-03, AI-02 |
| WU-DA-05 | 이상 신호 계산 | C | D | 3 | DA-04 |
| WU-AI-03 | KPI 인사이트 생성 | D | A | 3 | AI-01, DA-05 |
| WU-BE-04 | `/api/analyze` · 모듈 연결 | B | C | 3 | BE-03, DA-05, AI-03 |
| WU-FE-03 | 실제 API 연결 | A | B | 3 | BE-03, FE-01 |
| WU-FE-04 | 차트 (플랫폼 비교 · 추이) | A | B | 3 | FE-02 |
| WU-FE-05 | AI 질문 · 인사이트 UI | A | B | 3 | FE-03 |
| WU-FE-06 | 로딩 · 오류 · 반응형 | A | B | 3–4 | FE-03 |
| WU-BE-05 | 오류 처리 통일 | B | C | 3–4 | BE-04 |
| WU-AI-04 | AI 품질 테스트 (과잉 추론 방지) | D | A | 4 | AI-03 |
| WU-DA-06 | 데이터 · 실패 케이스 QA | C | D | 4 | BE-04 |
| WU-BE-06 | 배포 (Render · Vercel 연결) | B | C | 4 | BE-04, FE-03 |
| WU-INT-01 | 전체 통합 E2E 검증 | 전원 | 전원 | 4 | BE-06 |
| WU-INT-02 | 문서 · 발표 · 제출 | 전원 | 전원 | 5 | INT-01 |

---

## Day 1 — 공통 기반

### WU-COM-01 공통 데이터 구조 · API 계약 확정
- **담당:** 전원 (B 정리) · **리뷰:** 전원
- **내용:** 정규화 스키마 9개 필드, 플랫폼 컬럼 매핑, `/api/analyze` 응답 구조, 오류 코드 확정 후 `shared/contracts/` 에 기록

**완료 조건**
- [x] `shared/contracts/` 에 공통 데이터 스키마(9개 필드, 타입, 단위) 문서화 (`shared/contracts/README.md` 1장)
- [x] 쿠팡·네이버 → 공통 필드 매핑 표 확정 (README 1장 "플랫폼 컬럼 매핑". ⚠️ 팀 정의 템플릿 기준 — 실제 쿠팡·네이버 광고 리포트는 컬럼 구조가 달라 미지원, PR #20 `TEST_RESULTS.md` 4장)
- [x] `/api/preview`, `/api/analyze` 응답 JSON 예시 파일 커밋 (`preview_response.json`, `analyze_response.json`, `test_api.py` 에서 스키마 검증)
- [x] 오류 코드 목록 확정 (README 2장. `UNREADABLE_FILE` 은 PR #20 에서 추가 예정)
- [ ] 4명 전원이 PR에 승인(Approve) 표시 — ⏳ 계약을 바꾼 PR 중 4명 모두 승인한 PR 없음 (#6: C·D 승인, #9: B 승인, #17: 승인 없이 merge). 확정하려면 최종 계약 PR 에 전원 Approve 필요

### WU-COM-02 저장소 · 협업 환경 구성
- **담당:** B · **리뷰:** A

**완료 조건**
- [x] Collaborator 3명 초대 완료, 4명 모두 Clone 성공
- [ ] `main` 브랜치 보호 규칙 설정 (PR 필수, 승인 1명 이상) — ⏳ **설정 안 됨** (`gh api repos/.../branches/main` → `protected: false`, rulesets 0개). `02ea3d5`(README) 가 PR 없이 main 에 들어감. 관리자 직접 push 는 규칙이 있어도 우회될 수 있음 → 저장소 주인(Admin) 설정 필요
- [x] `.gitignore` 에 `.env`, `node_modules/`, `.venv/`, `__pycache__/` 포함
- [ ] 4명 모두 Branch → PR → Review → Merge 1회 이상 경험 — ⏳ B(#4)·C(#3)는 승인 후 merge. A(#1)·D(#2)는 리뷰 승인 없이 merge됨

### WU-COM-03 프로젝트 뼈대 생성
- **담당:** A (frontend), B (backend) · **리뷰:** C

**완료 조건**
- [x] `frontend/` Next.js + TypeScript 프로젝트 생성, `npm run dev` 로 기본 화면 표시
- [x] `backend/` FastAPI 프로젝트 생성, `requirements.txt` 작성
- [x] `backend/app/{routers,core,analysis,ai}` 폴더 및 빈 모듈 생성
- [x] `GET /health` → `{"status":"ok"}` 응답
- [x] 각 앱에 `.env.example` 커밋
- [x] README 의 실행 방법대로 다른 팀원이 로컬 실행 성공

### WU-DA-01 테스트 fixture 제작
- **담당:** C · **리뷰:** D

**완료 조건**
- [x] `shared/fixtures/` 에 쿠팡 8월·9월, 네이버 8월·9월 샘플 파일 (xlsx 또는 csv)
- [ ] 정답 파일 (`expected_kpis.json`) 에 전체·플랫폼별 KPI 및 변화율 기록 — ⏳ 전체 KPI·변화율(`kpis.change`)과 플랫폼별 최신 월 값(`by_platform`)은 있으나 **플랫폼별 변화율은 없음**. 응답 계약(TECH_SPEC 7-4)에 없는 값이라 정답 파일만 늘릴지 계약을 바꿀지 팀 판단 필요
- [x] 정답이 TECH_SPEC 5-1 예시(매출 +21.2%, 광고비 +28.0%, ROAS −14.2%p)와 일치
- [x] 실패용 fixture: 빈 파일, 컬럼 누락, 잘못된 숫자, 미지원 플랫폼 각 1개

---

## Day 2 — 담당별 개발

### WU-FE-01 파일 업로드 UI
- **담당:** A · **리뷰:** B

**완료 조건**
- [ ] 여러 `.xlsx`/`.csv` 파일을 한 번에 선택 가능
- [ ] 선택된 파일 목록(파일명, 크기) 표시, 개별 삭제 가능
- [ ] 허용되지 않은 확장자는 선택 단계에서 안내
- [ ] 미리보기 표 컴포넌트가 mock 데이터(계약 예시 JSON)로 렌더링

### WU-FE-02 KPI 대시보드 UI
- **담당:** A · **리뷰:** B

**완료 조건**
- [ ] KPI 카드 6개 (매출, 주문, 판매량, 광고비, 광고매출, ROAS) 렌더링
- [ ] 전월 대비 변화 표시, 증가/감소 색상 구분, ROAS는 `%p` 표기
- [ ] 금액 천 단위 콤마 + `원` 표기
- [ ] 계약 예시 JSON(mock)으로 전체 화면 렌더링 확인
- [ ] 값이 `null` 인 경우 `-` 로 표시

### WU-BE-01 FastAPI 서버 · 설정 · CORS
- **담당:** B · **리뷰:** C

**완료 조건**
- [x] `core/config.py` 에서 환경변수 로드 (`LLM_API_KEY`, `ALLOWED_ORIGINS`, `MAX_FILES`, `MAX_FILE_SIZE_MB`)
- [x] CORS 가 `ALLOWED_ORIGINS` 기반으로 설정, 로컬 프론트에서 `/health` 호출 성공
- [x] 라우터 분리 (`routers/health.py`, `preview.py`, `analyze.py`)
- [x] `/docs` (Swagger) 접근 가능

### WU-BE-02 Pydantic 스키마
- **담당:** B · **리뷰:** C

**완료 조건**
- [x] `schemas.py` 에 `PreviewResponse`, `AnalyzeResponse`, `KPIs`, `Comparison`, `Row`, `Signal`, `Insight`, `ErrorResponse` 정의
- [x] `shared/contracts/` 의 예시 JSON 이 스키마 검증을 통과하는 테스트 존재
- [x] 라우터 응답에 `response_model` 적용 (`/api/preview`, `/api/analyze`)

### WU-BE-03 파일 업로드 검증 · `/api/preview`
- **담당:** B · **리뷰:** C

**완료 조건**
- [x] 파일 0개 → `NO_FILES`, 개수 초과 → `TOO_MANY_FILES`, 크기 초과 → `FILE_TOO_LARGE`, 확장자 오류 → `UNSUPPORTED_FILE_TYPE`
- [x] 정상 파일에 대해 파일별 `platform`, `periods`, `row_count`, `columns`, `preview`(최대 10행) 반환
- [x] C 의 정규화 오류(`MISSING_COLUMNS` 등)가 오류 응답 형식으로 전달
- [x] `tests/test_api.py` 에 위 케이스 테스트 통과

### WU-DA-02 플랫폼 데이터 정규화
- **담당:** C · **리뷰:** D

**완료 조건**
- [x] `normalize.py` 에 `PLATFORM_COLUMN_MAP` 상수 (쿠팡·네이버)
- [x] xlsx·csv 모두 읽기 가능 (UTF-8, CP949 인코딩 CSV 처리) (`test_normalize.py::test_csv_with_bom_and_cp949`, `test_xlsx_gives_same_result_as_csv`)
- [x] 플랫폼 자동 판별 (컬럼 구조 기준, 불가 시 `UNKNOWN_PLATFORM`)
- [x] 숫자 정제 (`,`, `원`, 공백 제거), 실패 시 `INVALID_NUMBER` (파일·행·컬럼 정보 포함)
- [x] 필수 컬럼 누락 시 `MISSING_COLUMNS` (누락 목록 포함), 빈 파일 `EMPTY_FILE`
- [x] 출력 DataFrame 이 공통 스키마 9개 필드와 타입을 정확히 가짐 (`test_normalize_files_schema_and_dtypes`)
- [x] `test_analysis.py` 에 정상 4종 + 실패 4종 테스트 통과 (`test_normalize_files_each_normal_fixture`, `test_normalize_files_each_failure_fixture`)

### WU-DA-03 KPI 계산
- **담당:** C · **리뷰:** D

**완료 조건**
- [x] `kpi.py` 에서 매출·주문·판매량·광고비·광고매출 합계, ROAS 계산
- [x] 광고비 0 → ROAS `null` (`test_zero_ad_spend_gives_null_roas_not_zero_or_inf`)
- [x] 기간·플랫폼 단위 집계 가능 (`test_totals_aggregate_by_period_and_platform`)
- [x] fixture 기준 결과가 `expected_kpis.json` 과 정확히 일치 (`test_compute_kpis_matches_expected`, 배포 서버에서도 일치 확인)
- [x] 같은 입력으로 반복 실행 시 결과 동일 (`test_repeated_runs_and_input_order_give_identical_results`)

### WU-AI-01 LLM 클라이언트 · 실패 처리
- **담당:** D · **리뷰:** A

> #18 A 최종 승인/main ff214c2 병합 및 실제 main 비유료 493개 확인 후 D 서버 기능만 체크했다. #22 문서/opt-in 후속과 새 배포 UI/E2E는 별도 대기다. 실제 API 결과는 동일 AI 구현 29a90ea에서 실행한 기록이며 최신 단일 기준은 `D_WEDNESDAY_STATUS.md`다.

**완료 조건**
- [x] `ai/` 내 LLM 호출 함수가 API 키를 환경변수로만 읽음 (`OPENAI_API_KEY` 우선, `LLM_API_KEY` 호환; 실제 키는 커밋하지 않음)
- [x] 호출 1회당 타임아웃 적용 (`LLM_TIMEOUT_SECONDS`, 기본 30초 — 최신 TECH_SPEC과 일치)
- [x] JSON 파싱/검증 실패 시 1회 재시도 후 `llm_error` 반환 (`test_structured_client_retries_invalid_output_once`)
- [x] API 키 없음·네트워크 오류 시 예외가 밖으로 새지 않고 `llm_error` 반환 (`test_missing_api_key_is_normalized`, `test_structured_client_normalizes_provider_failure`)
- [x] 실패 경로를 모킹한 테스트 통과 (실제 main 493 passed/9 deselected, #22 통합 493 passed/10 deselected)

### WU-AI-02 질문 → 분석 계획 JSON (Planner)
- **담당:** D · **리뷰:** A

> #18 A 승인/main 반영 및 실제 main 회귀 확인 완료. 유료40문항은 동일 AI 구현 29a90ea의 기록이며 새 배포 UI는 별도다.

**완료 조건**
- [x] `planner.py` 가 질문 → `AnalysisPlan` (`metric`, `group_by`, `sort`, `limit`, `period`) 반환
- [x] 허용 값 외 구조 출력은 Pydantic 검증·1회 재시도 후 `llm_error`; 현재 계약에 없는 질문 조건·명시 조건 누락·임의 축소는 질문 정책과 `unrepresented_constraints`로 `unsupported_question` 안내
- [x] 최신 테스트 질문 세트 40개 작성 (`backend/tests/ai_quality_cases.json`: 지원 26, 미지원 14)
- [x] 실제 `gpt-6-luna` 테스트 질문 세트 40/40 통과(고정 회귀 기준, 최소 90% 이상; 일반 정확도 보장 아님)
  - 예: "광고 효율이 가장 안 좋은 플랫폼 어디야?" → `{"metric":"roas","group_by":"platform","sort":"asc"}`
- [x] 분석과 무관하거나 현재 계약으로 정확히 표현할 수 없는 질문은 `unsupported_question`

---

## Day 3 — 기능 확장 · 연결

### WU-DA-04 전월 · 플랫폼 비교 / 계획 실행
- **담당:** C · **리뷰:** D

**완료 조건**
- [x] `compare.py` 에서 최신 월 vs 직전 월 증감률(%) 및 ROAS 증감(%p) 계산 (실제 구현 위치는 `kpi.py::compute_kpis`, `compare.py` 는 플랫폼 비교·추이·계획 실행 담당)
- [x] 전월 값 0 → 증감률 `null` (`test_previous_zero_revenue_change_is_null`)
- [x] 데이터가 한 달뿐이면 `change` 는 `null`, 오류 없이 반환 (`test_single_month_has_no_previous`)
- [x] `by_platform`, `trend` 생성 (`test_build_comparison_matches_expected`)
- [x] `run_plan(df, plan)` 이 `AnalysisPlan` 을 받아 정렬·그룹·limit 적용 결과 반환 (`test_run_plan_*`, D 의 `AnalysisPlan` 모델로도 실행 확인)
- [x] fixture 결과가 매출 +21.2%, 광고비 +28.0%, ROAS −14.2%p 로 일치 (`test_compute_kpis_matches_expected`)

### WU-DA-05 이상 신호 계산
- **담당:** C · **리뷰:** D

**완료 조건**
- [x] `signals.py` 에 `ROAS_DOWN_WITH_SPEND_GROWTH`, `REVENUE_DOWN`, `LOW_ROAS_PLATFORM` 구현
- [x] 임계값이 상수로 분리됨 (`signals.py::LOW_ROAS_RATIO`)
- [x] 각 신호가 TECH_SPEC 6장의 필드를 포함
- [x] fixture 에서 `ROAS_DOWN_WITH_SPEND_GROWTH` 가 `ad_spend_change: 28.0`, `ad_revenue_change: 22.4`, `roas_change_pp: -14.2` 로 감지 (`test_detect_signals_matches_expected`)
- [x] 조건 미충족 데이터에서 신호가 발생하지 않는 테스트 통과 (`test_no_signals_gives_empty_list`, `test_single_month_has_no_previous`)

### WU-AI-03 KPI 인사이트 생성
- **담당:** D · **리뷰:** A

**완료 조건**
> #18 A 승인/main 반영 및 실제 main 회귀 확인 완료. API 근거/단위 확인과 배포 화면 확인을 구분한다.
- [x] `insight.py` 가 `kpis`, `comparison`, `signals`, (선택) `plan`/`answer` 를 받아 `Insight` 반환
- [x] 출력이 `summary`, `evidence`, `checks`, `actions`, `limitations` 로 분리
- [x] LLM은 자유 문장 대신 검증된 근거·점검·행동 ID만 선택하며, 데이터에 없는 원인·임의 숫자·메타데이터를 최종 응답에 넣을 수 없음
- [x] 후처리: 허용하지 않은 요약·점검·행동 ID는 `llm_error`, 잘못된 evidence ID는 해당 항목만 제거; 같은 범위의 상충 계산값은 호출 전에 차단
- [x] fixture 입력의 광고비 +28.0%, 광고매출 +22.4%, ROAS −14.2%p 근거를 서버가 기간·대상·지표·단위와 함께 표시 (main 근거/라우터 회귀 및29a90ea 실제 인사이트/API7개 기록; #22 전용 opt-in은 이번에 실행하지 않음)

### WU-BE-04 `/api/analyze` · 모듈 연결
- **담당:** B · **리뷰:** C

**완료 조건**
- [x] 처리 흐름(TECH_SPEC 1장 1~9단계)대로 C·D 모듈 호출
- [x] 응답이 `AnalyzeResponse` 스키마 검증 통과
- [x] `question` 없이 호출 가능, 300자 초과 시 `QUESTION_TOO_LONG`
- [x] LLM 실패 시에도 `kpis`/`comparison`/`rows`/`signals` 는 정상, `insight.status = "llm_error"`
- [x] fixture 4개 업로드 시 기대 KPI 반환 테스트 통과 (`tests/test_analysis.py::test_analyze_endpoint_returns_expected_deterministic_fields`, 배포 서버에서도 일치 확인)

### WU-FE-03 실제 API 연결
- **담당:** A · **리뷰:** B

**완료 조건**
- [ ] `lib/api/` 에 `preview`, `analyze` 클라이언트 함수 (`NEXT_PUBLIC_API_BASE_URL` 사용)
- [ ] `types/` 의 응답 타입이 계약과 일치
- [ ] 업로드 → `/api/preview` 결과로 파일 목록·플랫폼·기간·미리보기 표시
- [ ] 분석 버튼 → `/api/analyze` 결과로 KPI 카드 표시
- [ ] mock 데이터 의존 코드 제거

### WU-FE-04 차트 (플랫폼 비교 · 추이)
- **담당:** A · **리뷰:** B

**완료 조건**
- [ ] Recharts 플랫폼 비교 차트 (`comparison.by_platform` 의 매출·ROAS)
- [ ] Recharts 기간 추이 차트 (`comparison.trend` 의 매출·ROAS)
- [ ] 툴팁에 포맷된 값 표시
- [ ] 데이터가 한 기간뿐이어도 오류 없이 표시
- [ ] 이상 신호(`signals`) 배지 표시

### WU-FE-05 AI 질문 · 인사이트 UI
- **담당:** A · **리뷰:** B

**완료 조건**
- [ ] 질문 입력창 (300자 제한, 글자 수 표시) 및 예시 질문 버튼
- [ ] `summary`, `evidence`, `checks`, `actions`, `limitations` 가 구분된 섹션으로 표시
- [ ] `answer` 결과 표 표시
- [ ] `insight.status` 별 처리: `unsupported_question` → 예시 안내, `llm_error` → 재시도 안내 (KPI 영역은 유지)

### WU-FE-06 로딩 · 오류 · 반응형
- **담당:** A · **리뷰:** B

**완료 조건**
- [ ] 업로드·분석·AI 응답 중 로딩 표시, 중복 요청 방지 (버튼 비활성화)
- [ ] 오류 코드별 사용자 메시지 표시 (최소 `FILE_TOO_LARGE`, `TOO_MANY_FILES`, `MISSING_COLUMNS`, `INVALID_NUMBER`, `EMPTY_FILE`, 네트워크 오류)
- [ ] 모바일 폭(375px)에서 가로 스크롤 없이 주요 화면 확인 가능
- [ ] 콘솔 에러 없음

### WU-BE-05 오류 처리 통일
- **담당:** B · **리뷰:** C

**완료 조건**
- [x] `core/errors.py` 에 도메인 예외 → HTTP 응답 변환 핸들러
- [x] 모든 오류가 `{"error":{"code","message","details"}}` 형식
- [x] 예상치 못한 예외는 `INTERNAL_ERROR` (스택트레이스 응답 노출 금지, 서버 로그 기록)
- [x] TECH_SPEC 7-1 오류 코드 전체에 대한 API 테스트 통과

---

## Day 4 — 통합 · 검증 · 배포

### WU-AI-04 AI 품질 테스트 (과잉 추론 방지)
- **담당:** D · **리뷰:** A

**완료 조건**
> #18 A 승인/main 반영 및 실제 main 품질 회귀 확인 완료. 최신 문서/활용 사례의 main 반영은 #22 A 리뷰·병합 대기다.
- [x] 인사이트 품질 테스트 최소 5개 이상 구성 (`test_insight_safety.py`, `test_insight_number_grounding.py`, `ai_quality_runner.py`의 실제 인사이트 9개 시나리오)
- [x] 검증한 시나리오에서 사실 문장은 서버가 검증된 계산값으로 생성하고 호출자의 `plan`/`answer`를 보존 (숫자 변조 0건; 모든 임의 입력의 정확도 보장 아님)
- [x] 광고 소재·CTR·CPC·CVR·경쟁사·시장 상황 등 입력에 없는 원인을 모델이 단정문으로 생성하는 경로 제거 (허용되지 않은 자유 문장/ID 차단)
- [x] 필요한 추가 데이터와 현재 확인 불가 범위를 서버의 `limitations`에 기술 (단일 월, ROAS 계산 불가, 불연속 월, 신호 없음 포함)
- [ ] 최신 테스트 결과와 AI 활용 사례를 `DevelopDoc/AI_RELIABILITY_IMPROVEMENTS.md`, `AI_INSIGHT_SAFETY_TEST_REPORT.md`, `AI_USAGE_CASES.md`에 기록하고 main 반영 (#22 준비 완료, A 리뷰·병합 대기)

### WU-DA-06 데이터 · 실패 케이스 QA
- **담당:** C · **리뷰:** D

**완료 조건**
- [x] 실패 테스트 전 항목 확인: 빈 파일, 누락 컬럼, 잘못된 숫자, 파일 크기 초과, 파일 개수 초과, 미지원 확장자, 미지원 플랫폼 (`tests/test_failure_cases.py`, 경계값·손상 파일 포함)
- [x] 각 케이스가 API 에서 올바른 오류 코드 반환 (`/api/preview`·`/api/analyze` 양쪽, 로컬 pytest + 배포 서버 확인. 손상 파일은 `UNREADABLE_FILE`(422)로 추가, PR #20)
- [x] 각 케이스가 화면에서 이해 가능한 메시지로 표시 (9/30 배포 프론트에서 7종 + 손상 파일 확인, `TEST_RESULTS.md` 3장. 개수·크기 초과 때 파일 목록 처리는 PR #25 에서 개선 중)
- [ ] 실제 형식에 가까운 샘플 데이터로 KPI 수기 검산 1회 이상 — ⏳ 스마트스토어 판매 샘플은 월 요약 행과 일치 확인(요약 행 중복 집계 수정, PR #20). 쿠팡·네이버 광고 샘플은 컬럼명·파일 구조가 템플릿과 달라 [#21](https://github.com/tickle1231102-cmd/AI_seller_insight/issues/21) 의 팀 결정 대기
- [x] 테스트 결과 기록 (`DevelopDoc/TEST_RESULTS.md`, AI 항목 6장은 D 작성)

### WU-BE-06 배포 (Render · Vercel 연결)
- **담당:** B · **리뷰:** C

**완료 조건**
- [x] Render 에 Backend 배포, 배포 URL `/health` 정상
- [x] `main` 에 `backend/**` 변경이 merge 되면 자동 재배포 (PR #19, GitHub Actions → Render Deploy Hook). 9/30 수동 실행 성공 → Render Live 확인. 워크플로는 배포 '요청'만 하므로 빌드 성공은 Render Events 에서 확인
- [x] Render 환경변수(API 키, `ALLOWED_ORIGINS`) 설정 — 9/30 API 키 등록, 배포 서버 `insight.status=ok` 확인. `LLM_MODEL` 을 넣지 않으면 기본값 `gpt-6-luna`
- [x] Vercel 에 Frontend 배포, `NEXT_PUBLIC_API_BASE_URL` 이 Render URL (9/30 배포 번들에 Render 주소 포함 확인)
- [x] 배포된 Frontend 에서 CORS 오류 없이 `/api/analyze` 호출 성공 (9/30 `ai-seller-insight.vercel.app` 에서 fixture 4개 → 200, KPI `expected_kpis.json` 일치)
- [x] 저장소·빌드 로그·프론트 번들에 API 키 노출 없음
- [x] 배포 URL 을 README 에 기재

### WU-INT-01 전체 통합 E2E 검증
- **담당:** 전원 · **리뷰:** 전원

**완료 조건**
- [ ] 배포 환경에서 fixture 4개 업로드 → 미리보기 → 분석 → KPI → 차트 → 신호 → 질문 → 인사이트 흐름 성공
- [ ] 화면 KPI 값이 `expected_kpis.json` 과 일치
- [ ] LLM 장애 상황(키 제거 등)에서 KPI 는 표시되고 AI 영역만 오류 안내
- [ ] 실패 케이스 6종(빈 파일, 누락 컬럼, 잘못된 숫자, LLM 장애, 잘못된 질문, 파일 크기 초과) 시연 가능
- [ ] 발견 버그는 Issue 로 등록 후 수정 PR Merge

---

## Day 5 — 제출

### WU-INT-02 문서 · 발표 · 제출
- **담당:** 전원 · **리뷰:** 전원
- **원칙:** Day 5 에는 새 기능을 추가하지 않는다 (버그 수정만).

**완료 조건**
- [ ] README 최신화 (배포 URL, 실행 방법, 스크린샷)
- [ ] PRD / TECH_SPEC 가 실제 구현과 일치하도록 갱신
- [ ] WORK_UNITS 의 모든 체크박스 상태 갱신
- [ ] FINAL_CHECKLIST 전 항목 확인
- [ ] 발표 자료 및 시연 시나리오 준비, 리허설 1회
- [ ] 최종 배포 버전 태그 (`v1.0.0`) 생성 및 제출
