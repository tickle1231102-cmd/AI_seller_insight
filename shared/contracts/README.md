# shared/contracts — 공통 계약 (초안)

> WU-COM-01. **변경 시 전원 합의 필수.** 4명 전원이 PR 에 Approve 해야 확정된다.
> 원본 명세는 [TECH_SPEC.md](../../DevelopDoc/TECH_SPEC.md) 4·6·7장. 이 폴더는 그 내용을 코드·테스트가 참조할 수 있는 형태로 옮긴 것이다.

| 파일 | 내용 | 사용처 |
|---|---|---|
| `preview_response.json` | `POST /api/preview` 응답 예시 (TECH_SPEC 7-3) | `backend/tests/test_api.py` 스키마 검증, 프론트 mock |
| `analyze_response.json` | `POST /api/analyze` 응답 예시 (TECH_SPEC 7-4) | 〃 |

- 백엔드 스키마: `backend/app/schemas.py`
- 프론트 타입: `frontend/types/api.ts`

## 1. 공통 데이터 스키마 (정규화 결과)

| 필드 | 타입 | 설명 |
|---|---|---|
| `period` | string (`YYYY-MM`) | 기간 |
| `platform` | `coupang` \| `naver` | 플랫폼 |
| `product_id` | string | 상품 ID |
| `product_name` | string | 상품명 |
| `revenue` | number (원) | 매출 |
| `orders` | integer | 주문 수 |
| `units` | integer | 판매 수량 |
| `ad_spend` | number (원) | 광고비 |
| `ad_revenue` | number (원) | 광고 전환매출 |

### 플랫폼 컬럼 매핑

| 공통 필드 | 쿠팡 | 네이버 |
|---|---|---|
| `revenue` | 총매출 | 판매금액(순) |
| `orders` | 주문 | 상품결제건수 |
| `units` | 판매량 | 결제상품수량 |
| `ad_spend` | 광고비 | 광고비용 |
| `ad_revenue` | 광고매출 | 전환매출 |
| `product_id` | 상품ID | 상품ID |
| `product_name` | 상품명 | 상품명 |
| `period` | 파일명의 `_YYYY-MM` | 파일명의 `_YYYY-MM` |

> `period` 는 원본 컬럼이 아니라 **파일명**에서 뽑는다 (예: `coupang_2026-09.csv` → `2026-09`). 규칙은 `\d{4}-(0[1-9]|1[0-2])` 이고, 없으면 `INVALID_PERIOD` 오류.
> 플랫폼은 파일명이 아니라 **컬럼 구조**로 판별한다 (지표 컬럼 5개 중 3개 이상 일치하는 쪽, 동률·미달이면 `UNKNOWN_PLATFORM`).
> `preview_file` 의 `columns` 는 맨 앞이 `product_name` 이고 그 뒤가 원본 지표 컬럼명이다. 프론트 미리보기 표가 `columns` 를 행의 키로 쓰기 때문이다.

## 2. 오류 응답

```json
{ "error": { "code": "MISSING_COLUMNS", "message": "…", "details": { "file": "coupang_2026-09.xlsx", "missing": ["광고매출"] } } }
```

| code | HTTP | details 키 |
|---|---|---|
| `NO_FILES` | 400 | — |
| `TOO_MANY_FILES` | 400 | `max_files`, `count` |
| `FILE_TOO_LARGE` | 413 | `file`, `max_mb` |
| `UNSUPPORTED_FILE_TYPE` | 400 | `file` |
| `EMPTY_FILE` | 422 | `file` |
| `MISSING_COLUMNS` | 422 | `file`, `missing` |
| `INVALID_NUMBER` | 422 | `file`, `row`, `column`, `value` (`row` 는 헤더를 뺀 데이터 행 기준 1부터) |
| `INVALID_PERIOD` | 422 | `file` (파일명에서 `_YYYY-MM` 을 찾지 못함) |
| `UNKNOWN_PLATFORM` | 422 | `file` |
| `QUESTION_TOO_LONG` | 400 | `max_length` |
| `NOT_FOUND` | 404 | — (없는 주소) |
| `METHOD_NOT_ALLOWED` | 405 | — (잘못된 요청 방식) |
| `INVALID_REQUEST` | 422 | `errors`: `[{field, message}]` (요청 형식 오류) |
| `INTERNAL_ERROR` | 500 | — |

`details` 키 이름은 `frontend/lib/api/client.ts` 의 오류 메시지 함수가 사용한다 (`file`, `missing`, `row`, `column`).
모든 모듈은 `app.core.errors.AppError(code, message, status_code, details)` 로 오류를 던진다.

## 3. B ↔ C / D 호출 계약

B 의 `routers/preview.py`, `routers/analyze.py` 가 아래 함수를 호출한다. C 함수는 모두 구현돼 있다.

| 단계 (TECH_SPEC 1장) | 호출 | 위치 | 상태 |
|---|---|---|---|
| preview | `normalize.preview_file(filename: str, content: bytes) -> dict` | `analysis/normalize.py` (C) | 구현됨 |
| 2·3 정규화 | `normalize.normalize_files(files: list[tuple[str, bytes]]) -> DataFrame` | `analysis/normalize.py` (C) | 구현됨 |
| 4 KPI | `kpi.compute_kpis(df) -> dict` (응답 `kpis`) | `analysis/kpi.py` (C) | 구현됨 |
| 5 비교 | `compare.build_comparison(df) -> dict` (응답 `comparison`) | `analysis/compare.py` (C) | 구현됨 |
| 6 신호 | `signals.detect_signals(kpis, comparison) -> list[dict]` | `analysis/signals.py` (C) | 구현됨 |
| 7 질문 해석 | `create_analysis_plan(question: str) -> PlannerResult` | `ai/planner.py` (D) | D 브랜치 `feat/ai-planner-openai` |
| 7 계획 실행 | `compare.run_plan(df, plan: AnalysisPlan) -> list[dict]` | `analysis/compare.py` (C) | 구현됨 |
| 8 인사이트 | `create_insight(kpis, comparison, signals, *, plan=None, answer=None) -> Insight` | `ai/insight.py` (D) | D 브랜치 `feat/ai-planner-openai` |

- 응답 `rows` 는 B 가 정규화 DataFrame 을 `df.to_dict(orient="records")` 로 변환한다.
- AI 단계(7·8)에서 어떤 예외가 나도 B 가 잡아 `insight.status = "llm_error"` 로 바꾸고 `kpis`/`comparison`/`rows`/`signals` 는 정상 반환한다.
- `PlannerResult.status == "unsupported_question"` 이면 인사이트를 호출하지 않고 `insight.summary` 에 `reason` 을 담는다.

## 4. 환경변수

`backend/.env.example` 참고. API 키 변수명은 TECH_SPEC 10장 기준 `LLM_API_KEY`.
`.env` 는 `core/config.py` 에서 로드되며 `os.environ` 에도 반영된다.

## 5. C 분석 함수 동작 규칙

정답 데이터는 `shared/fixtures/expected_kpis.json` 이고 `backend/tests/test_analysis.py` 가 이 규칙을 검증한다.

**정규화 (`normalize_files`)**
- 금액·수량은 정수로 반올림한다. 빈 숫자 셀은 0.
- 행 순서는 `period` → `platform` → `product_id`. 여러 파일의 오류는 `details.file` 로 구분한다.

**KPI·비교 (`compute_kpis`, `build_comparison`)**
- 비교 기간은 데이터에 있는 최신 월과 그 직전 월이다 (달력상 바로 앞달이 아니어도 된다). 월이 하나뿐이면 `previous_period`, `previous`, `change` 의 모든 값이 `null`.
- 증감률은 소수 첫째 자리 반올림. 분모(전월 값)가 0 이면 `null`. `roas_change_pp` 는 반올림 전 ROAS 끼리 뺀 값이다.
- ROAS = Σ`ad_revenue` ÷ Σ`ad_spend` × 100. 그룹·플랫폼별 ROAS 도 행 평균이 아니라 합계로 다시 계산하고, `ad_spend` 합이 0 이면 `null`.
- `comparison.by_platform` 은 최신 월 기준(플랫폼 이름순), `trend` 는 전체 기간(오래된 월부터).

**신호 (`detect_signals`)**
- `ROAS_DOWN_WITH_SPEND_GROWTH`, `REVENUE_DOWN` 은 `platform: "all"`. `LOW_ROAS_PLATFORM` 은 플랫폼 ROAS < 전체 ROAS × 0.8 (같으면 신호 아님)이고 그 플랫폼 이름을 `platform` 에 넣는다.
- 증감 값이 `null` 이면 그 신호는 만들지 않는다. 신호가 없으면 `[]`.

**질문 실행 (`run_plan`)** — `plan` 은 `AnalysisPlan` 객체 또는 같은 키의 dict.

| 항목 | 값이 `null` 일 때 |
|---|---|
| `sort` | `desc` |
| `limit` | 5 |
| `period` | 최신 월 |
| `group_by` | 전체 합계 1행 |

- 예외: `group_by="period"` 이고 `period` 가 `null` 이면 월별 비교가 목적이므로 **전체 기간**을 쓴다. `period` 를 지정하면 그 월 1행.
- 답 행의 키: 그룹 키 + 지표 이름. `platform` → `{platform, <metric>}`, `period` → `{period, <metric>}`, `product` → `{product_id, product_name, <metric>}` (두 플랫폼 합산), `group_by` 없음 → `{<metric>}`.
- 지표 값이 `null` (ROAS 분모 0) 인 그룹은 정렬 방향과 상관없이 맨 뒤. 동률은 그룹 키 순.
- 업로드된 데이터에 없는 월은 `AppError("PERIOD_NOT_FOUND", …, 422, {period, available})` 를 던진다. 메시지는 사용자에게 그대로 보여도 되는 문구다 (`summary` 로 나간다).
