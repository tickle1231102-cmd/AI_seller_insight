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
| `period` | **미정** | **미정** |
| `product_id` | **미정** | **미정** |
| `product_name` | **미정** | **미정** |

> ⚠️ `period` / `product_id` / `product_name` 의 원본 컬럼(또는 파일명 규칙)은 TECH_SPEC 에 없다. C 가 fixture 제작 시 확정해 이 표에 채운다.

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
| `INVALID_NUMBER` | 422 | `file`, `row`, `column` |
| `UNKNOWN_PLATFORM` | 422 | `file` |
| `QUESTION_TOO_LONG` | 400 | `max_length` |
| `INTERNAL_ERROR` | 500 | — |

`details` 키 이름은 `frontend/lib/api/client.ts` 의 오류 메시지 함수가 사용한다 (`file`, `missing`, `row`, `column`).
모든 모듈은 `app.core.errors.AppError(code, message, status_code, details)` 로 오류를 던진다.

## 3. B ↔ C / D 호출 계약

B 의 `routers/preview.py`, `routers/analyze.py` 가 아래 함수를 호출한다. C 함수는 시그니처만 정의돼 있고 본문은 C 가 구현한다.

| 단계 (TECH_SPEC 1장) | 호출 | 위치 | 상태 |
|---|---|---|---|
| preview | `normalize.preview_file(filename: str, content: bytes) -> dict` | `analysis/normalize.py` (C) | 시그니처만 |
| 2·3 정규화 | `normalize.normalize_files(files: list[tuple[str, bytes]]) -> DataFrame` | `analysis/normalize.py` (C) | 시그니처만 |
| 4 KPI | `kpi.compute_kpis(df) -> dict` (응답 `kpis`) | `analysis/kpi.py` (C) | 시그니처만 |
| 5 비교 | `compare.build_comparison(df) -> dict` (응답 `comparison`) | `analysis/compare.py` (C) | 시그니처만 |
| 6 신호 | `signals.detect_signals(kpis, comparison) -> list[dict]` | `analysis/signals.py` (C) | 시그니처만 |
| 7 질문 해석 | `create_analysis_plan(question: str) -> PlannerResult` | `ai/planner.py` (D) | D 브랜치 `feat/ai-planner-openai` |
| 7 계획 실행 | `compare.run_plan(df, plan: AnalysisPlan) -> list[dict]` | `analysis/compare.py` (C) | 시그니처만 |
| 8 인사이트 | `create_insight(kpis, comparison, signals, *, plan=None, answer=None) -> Insight` | `ai/insight.py` (D) | D 브랜치 `feat/ai-planner-openai` |

- 응답 `rows` 는 B 가 정규화 DataFrame 을 `df.to_dict(orient="records")` 로 변환한다.
- AI 단계(7·8)에서 어떤 예외가 나도 B 가 잡아 `insight.status = "llm_error"` 로 바꾸고 `kpis`/`comparison`/`rows`/`signals` 는 정상 반환한다.
- `PlannerResult.status == "unsupported_question"` 이면 인사이트를 호출하지 않고 `insight.summary` 에 `reason` 을 담는다.

## 4. 환경변수

`backend/.env.example` 참고. API 키 변수명은 TECH_SPEC 10장 기준 `LLM_API_KEY`.
`.env` 는 `core/config.py` 에서 로드되며 `os.environ` 에도 반영된다.
