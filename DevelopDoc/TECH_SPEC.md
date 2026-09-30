# TECH_SPEC — Seller Insight AI

| 항목 | 내용 |
|---|---|
| 문서 | 기술 명세 |
| 주 담당 | B (Backend / 통합) |
| 관련 문서 | [PRD.md](PRD.md), [WORK_UNITS.md](WORK_UNITS.md) |

---

## 1. 시스템 아키텍처

```text
┌──────────────────────────┐
│ Frontend (Vercel)        │  Next.js · React · TypeScript · Recharts
│  upload / dashboard /    │
│  insight                 │
└────────────┬─────────────┘
             │ HTTPS (multipart/form-data, JSON)
             ▼
┌──────────────────────────┐
│ Backend (Render)         │  FastAPI · Pydantic
│  routers/ → 요청 검증    │
│      │                   │
│      ├─ analysis/ (C)    │  pandas · openpyxl
│      │   normalize → kpi → compare → signals
│      │                   │
│      └─ ai/ (D)          │  LLM API
│          planner → (analysis 실행) → insight
└────────────┬─────────────┘
             │ JSON { kpis, comparison, rows, signals, insight }
             ▼
        Frontend 렌더링
```

### 처리 흐름 (`/api/analyze`)

```text
1. 파일 수신 및 개수·크기·확장자 검증        (B)
2. 파일 파싱 → DataFrame                     (C: normalize)
3. 플랫폼 판별 + 공통 스키마로 정규화        (C: normalize)
4. KPI 계산                                   (C: kpi)
5. 전월·플랫폼 비교                           (C: compare)
6. 이상 신호 계산                             (C: signals)
7. 질문이 있으면 → 분석 계획 JSON 생성        (D: planner)
   → 계획에 따라 pandas 계산 실행            (C: compare.run_plan)
8. KPI/비교/신호/질문 결과 → 인사이트 생성    (D: insight)
9. 응답 JSON 조립 및 반환                     (B)
```

LLM 실패 시 7·8단계만 실패 처리하고 1~6단계 결과는 정상 반환한다.

## 2. 기술 스택

| 영역 | 기술 | 비고 |
|---|---|---|
| Frontend | Next.js (App Router), React, TypeScript | |
| Chart | Recharts | |
| Backend | Python 3.11+, FastAPI, Uvicorn | |
| Validation | Pydantic v2 | 요청·응답·AI JSON 검증 |
| Data | pandas, openpyxl | XLSX 읽기 |
| AI | LLM API (JSON 출력 모드 사용) | |
| Test | pytest (backend) | |
| Deploy | Vercel (FE), Render (BE) | |

## 3. 디렉터리 구조 및 소유권

```text
.
├─ frontend/                      ← A
│  ├─ app/
│  ├─ components/
│  ├─ features/
│  │  ├─ upload/
│  │  ├─ dashboard/
│  │  └─ insight/
│  ├─ lib/api/                    # API 클라이언트
│  └─ types/                      # shared/contracts 와 동기화된 TS 타입
├─ backend/
│  ├─ app/
│  │  ├─ main.py                  ← B
│  │  ├─ schemas.py               ← B
│  │  ├─ routers/                 ← B  (health.py, preview.py, analyze.py)
│  │  ├─ core/                    ← B  (config.py, errors.py, uploads.py)
│  │  ├─ analysis/                ← C
│  │  │  ├─ normalize.py
│  │  │  ├─ kpi.py
│  │  │  ├─ compare.py
│  │  │  └─ signals.py
│  │  └─ ai/                      ← D
│  │     ├─ client.py             # OpenAI 호출 · 타임아웃 · 재시도
│  │     ├─ models.py             # AnalysisPlan, PlannerResult, InsightDraft(LLM 생성용), Insight(응답용)
│  │     ├─ planner.py
│  │     ├─ insight.py
│  │     └─ prompts/
│  ├─ tests/
│  │  ├─ test_api.py, test_analyze.py                ← B
│  │  ├─ test_analysis.py, test_normalize.py         ← C
│  │  └─ test_ai.py, test_insight.py, test_ai_live.py ← D
│  └─ requirements.txt
├─ shared/
│  ├─ contracts/                  ← 전원 합의 / B 관리
│  └─ fixtures/                   ← C
└─ DevelopDoc/
```

## 4. 공통 데이터 스키마 (정규화 결과)

> 변경 시 전원 합의 필수. 원본 정의는 `shared/contracts/` 에 둔다.

| 필드 | 타입 | 설명 |
|---|---|---|
| `period` | string (`YYYY-MM`) | 기간 (원본 컬럼이 아니라 **파일명**의 `YYYY-MM` 에서 추출. 앞뒤에 숫자가 붙지 않은 것, 예: `coupang_2026-09.csv`) |
| `platform` | string (`coupang` \| `naver` \| `naver_store`) | 플랫폼 (`naver_store` 는 4-3 참고) |
| `product_id` | string | 상품 ID |
| `product_name` | string | 상품명 |
| `revenue` | integer (원) | 매출 |
| `orders` | integer | 주문 수 |
| `units` | integer | 판매 수량 |
| `ad_spend` | integer (원) | 광고비 |
| `ad_revenue` | integer (원) | 광고 전환매출 |

### 4-1. 플랫폼 컬럼 매핑

| 공통 필드 | 쿠팡 | 네이버 |
|---|---|---|
| `revenue` | 총매출 | 판매금액(순) |
| `orders` | 주문 | 상품결제건수 |
| `units` | 판매량 | 결제상품수량 |
| `ad_spend` | 광고비 | 광고비용 |
| `ad_revenue` | 광고매출 | 전환매출 |
| `product_id` | 상품ID | 상품ID |
| `product_name` | 상품명 | 상품명 |
| `period` | 파일명의 `YYYY-MM` | 파일명의 `YYYY-MM` |

매핑 테이블은 `analysis/normalize.py` 의 `PLATFORM_COLUMN_MAP` 상수로 관리하며, 새 플랫폼은 이 매핑 추가만으로 지원할 수 있도록 한다.

### 4-2. 정규화 규칙

- 숫자 컬럼의 `,`, `원`, 공백 제거 후 숫자 변환
- 변환 불가 값 → `INVALID_NUMBER` 오류 (행 번호·컬럼명 포함)
- 필수 컬럼 누락 → `MISSING_COLUMNS` 오류 (누락 컬럼 목록 포함)
- 데이터 행 0개 → `EMPTY_FILE` 오류
- 빈 숫자 셀 → 0 으로 처리
- 금액·수량 5개 필드(`revenue`, `orders`, `units`, `ad_spend`, `ad_revenue`)는 정수로 반올림 (Python `round` 라 `.5` 는 짝수 쪽으로)
- 파일명에서 기간을 찾지 못함 → `INVALID_PERIOD` 오류. 기간은 `YYYY-MM` 이 우선이고, 없으면 날짜 범위(`YYYYMMDD-YYYYMMDD` 등, 첫·끝 날짜의 중간이 속한 월)를 쓴다. 예: `sales_20260830-20260928.xlsx` → `2026-09`
- 셀 값 `-` 는 스마트스토어 판매 분석 파일에서만 0 으로 본다. 그 외 파일에서는 `INVALID_NUMBER`

### 4-3. 스마트스토어 판매 분석 (`naver_store`)

네이버 스마트스토어 통계 > 판매 분석(SALES) 내보내기 파일을 올리면 `platform="naver_store"` 로 정규화한다. 광고 리포트(`naver`)와 같은 판매액이 겹칠 수 있으므로 **합산하지 않고 분리**한다.

- 판별: 컬럼에 `채널상품번호`, `채널상품명`, `판매금액(총)` 이 모두 있으면 스토어 판매 파일이다.
- 매핑: `revenue`=판매금액(순), `orders`=상품결제건수, `units`=결제상품수량. `ad_spend`·`ad_revenue` 는 0. 추가 지표 `gross_revenue`(판매금액(총)), `visits`(방문수), `refund_count`, `refund_amount`, `discount_amount`(전체 할인액) 는 스토어 행에만 값이 있다 (그 외 행은 응답에서 필드 자체가 빠진다).
- 기간: 행의 `날짜` 범위 중간이 속한 월, 없으면 파일명. 일자별 행은 월·상품별로 합친다.
- **`kpis`·`comparison`·`signals`·질문 실행(`run_plan`)은 `naver_store` 행을 제외하고 계산**한다. `rows` 와 `store` 에만 나온다. 스토어 파일만 올리면 제외할 행이 없으므로 그 행으로 계산한다.
- `store` (응답 최상위, 스토어 파일이 없으면 `null`): 스토어 데이터의 최신 월·달력상 앞달 기준(앞달 자료가 없으면 `previous`/`change` 는 `null`) `current`/`previous`/`change`(퍼널·환불률·할인율·객단가), 상품별 `products`(최대 10개), `trend`.
- 방문·검색어·고객 분석 파일은 아직 지원하지 않으며 `UNSUPPORTED_DATASET` 오류를 낸다 (P1).

### 4-4. 지원 입력 범위 (#21 결정)

지원하는 입력은 **팀 정의 통합 템플릿 `coupang`·`naver`**(4-1)와 **스마트스토어 판매 분석 `naver_store`**(4-3)뿐이다. 플랫폼은 파일명이 아니라 컬럼 구조로 판별한다. `채널상품번호`·`채널상품명`·`판매금액(총)` 세 컬럼이 모두 있으면 `naver_store`, 아니면 `coupang`·`naver` 중 지표 컬럼 5개가 더 많이 일치하는 쪽이다 (3개 이상 일치, 동률·미달이면 `UNKNOWN_PLATFORM`). 3개 이상 겹치지만 필요한 컬럼이 빠진 파일은 `MISSING_COLUMNS` 다.

| 실제 형식 리포트 (합성 샘플로 확인) | 결과 | 이유 |
|---|---|---|
| 네이버 스마트스토어 판매 분석 | 지원 (`naver_store`) | 4-3 |
| 쿠팡 판매 리포트 | `UNKNOWN_PLATFORM` | 지표 5개 중 `주문`·`판매량`만 일치, 광고 컬럼 없음 |
| 네이버 쇼핑검색광고 리포트 | `UNKNOWN_PLATFORM` | `총비용`·`총 전환매출액` 등 컬럼명이 다르고 판매 컬럼 없음 |
| 쿠팡 광고 리포트 | `UNKNOWN_PLATFORM` | `광고비`만 일치 |

- 샘플은 공식 도움말·화면 지표를 바탕으로 만든 합성 데이터라 실제 내보내기와 완전히 같다는 보장은 없다. 상세: `DevelopDoc/TEST_RESULTS.md` 4장, #21.
- 알려진 한계: 스마트스토어 판매 파일에서 한 월 안에 월 요약 행과 일자별 `전체` 행만 있고 상품 행이 없으면, 두 요약 행이 겹쳐 집계될 수 있다 (`TEST_RESULTS.md` 4장).
- 향후 과제 (이번 범위 제외)
  - 부분 리포트 합산: 쿠팡 판매·광고 파일을 각각 판별해 플랫폼·월 단위로 합산. 먼저 전환매출 기준(1일/14일), 매출 기준(`매출(원)`/`총 매출(원)`), 판매·광고 기간 불일치 경고, 4-3 KPI 범위와의 관계를 정해야 한다.
  - 상품 단위 병합: 네이버 쇼핑검색광고 리포트에는 상품 키가 없어 보류.

## 5. KPI 계산 명세

| KPI | 계산식 | 단위 |
|---|---|---|
| `revenue` | Σ revenue | 원 |
| `orders` | Σ orders | 건 |
| `units` | Σ units | 개 |
| `ad_spend` | Σ ad_spend | 원 |
| `ad_revenue` | Σ ad_revenue | 원 |
| `roas` | ad_revenue ÷ ad_spend × 100 | % |
| 증감률 (`*_change`) | (당월 − 전월) ÷ 전월 × 100 | % |
| ROAS 증감 (`roas_change_pp`) | 당월 ROAS − 전월 ROAS | %p |

- 반올림: 표시용 값은 소수 첫째 자리 (`round(x, 1)`), 내부 계산은 원값 유지
- 분모가 0인 경우 `null` 반환 (0 이나 무한대로 표시하지 않음)
- 비교 대상 기간: 업로드 데이터의 최신 월 vs **달력상 바로 앞달**. 앞달 자료가 없으면(월이 하나뿐이거나 7월+9월처럼 건너뛴 경우) 증감은 모두 `null` (`kpis.previous_period` 도 `null`)

### 5-1. 검증용 예시 (fixture 정답)

| | 8월 | 9월 | 변화 |
|---|---|---|---|
| 매출 | 10,400,000 | 12,600,000 | +21.2% |
| 광고비 | 1,500,000 | 1,920,000 | +28.0% |
| ROAS | 326.7% | 312.5% | −14.2%p |

## 6. 이상 신호 명세

| signal | 조건 | 포함 필드 |
|---|---|---|
| `ROAS_DOWN_WITH_SPEND_GROWTH` | ad_spend_change > 0 이고 roas_change_pp < 0 | ad_spend_change, ad_revenue_change, roas_change_pp |
| `REVENUE_DOWN` | revenue_change < 0 | revenue_change |
| `LOW_ROAS_PLATFORM` | 플랫폼 ROAS < 전체 ROAS × 0.8 | platform, roas, overall_roas |

각 신호는 `platform` 필드(`all` 또는 플랫폼명)를 포함한다. 임계값은 `signals.py` 상수로 관리한다.

## 7. API 명세

### 7-1. 공통

- Base URL: 환경변수 `NEXT_PUBLIC_API_BASE_URL`
- 파일 제한: 최대 **10개**, 파일당 **5MB**, 확장자 `.xlsx`, `.csv`
- 질문 길이: 최대 **300자**
- 오류 응답 형식:

```json
{
  "error": {
    "code": "MISSING_COLUMNS",
    "message": "coupang_2026-09.xlsx 파일에 '광고매출' 컬럼이 없습니다.",
    "details": { "file": "coupang_2026-09.xlsx", "missing": ["광고매출"] }
  }
}
```

| code | HTTP | 설명 |
|---|---|---|
| `NO_FILES` | 400 | 업로드 파일 없음 |
| `TOO_MANY_FILES` | 400 | 파일 개수 초과 |
| `FILE_TOO_LARGE` | 413 | 파일 크기 초과 |
| `UNSUPPORTED_FILE_TYPE` | 400 | 허용되지 않은 확장자 |
| `EMPTY_FILE` | 422 | 데이터 행 없음 |
| `UNREADABLE_FILE` | 422 | 파일을 표로 읽을 수 없음 (손상된 xlsx, 해독할 수 없는 인코딩 등) |
| `MISSING_COLUMNS` | 422 | 필수 컬럼 누락 |
| `INVALID_NUMBER` | 422 | 숫자 변환 실패 |
| `UNKNOWN_PLATFORM` | 422 | 플랫폼 판별 불가 |
| `UNSUPPORTED_DATASET` | 422 | 스마트스토어 방문·검색어·고객 분석 파일 (판매 분석만 지원) |
| `INVALID_PERIOD` | 422 | 파일명에서 기간(`YYYY-MM` 또는 날짜 범위)을 찾지 못함 |
| `QUESTION_TOO_LONG` | 400 | 질문 길이 초과 |
| `NOT_FOUND` | 404 | 없는 주소 |
| `METHOD_NOT_ALLOWED` | 405 | 잘못된 요청 방식 |
| `INVALID_REQUEST` | 422 | 요청 형식 오류 (`details.errors: [{field, message}]`) |
| `HTTP_ERROR` | 원래 상태 코드 | 위에 없는 그 밖의 프레임워크 HTTP 오류 |
| `INTERNAL_ERROR` | 500 | 기타 서버 오류 (스택트레이스는 응답에 노출하지 않고 서버 로그에만 기록) |

- 모든 오류는 위 `{"error":{code,message,details}}` 형식이다. **허용된 Origin(`ALLOWED_ORIGINS`)에서 보낸 요청**에는 500 을 포함한 오류 응답에도 CORS 헤더가 붙는다. Origin 이 없거나 허용되지 않은 Origin 이면 `Access-Control-Allow-Origin` 은 붙지 않는다.
- 오류별 `details` 키는 [`shared/contracts/README.md`](../shared/contracts/README.md) 2장 참고.

### 7-2. `GET /health`

```json
{ "status": "ok" }
```

### 7-3. `POST /api/preview`

- Content-Type: `multipart/form-data`
- Body: `files` (복수)

```json
{
  "files": [
    {
      "filename": "coupang_2026-09.xlsx",
      "platform": "coupang",
      "periods": ["2026-09"],
      "row_count": 42,
      "columns": ["product_name", "총매출", "주문", "판매량", "광고비", "광고매출"],
      "preview": [ { "product_name": "...", "총매출": 120000 } ]
    }
  ]
}
```

`preview` 는 파일당 최대 10행. `columns` 는 맨 앞이 `product_name` 이고 그 뒤가 원본 지표 컬럼명이다 (프론트 미리보기 표가 `columns` 를 행의 키로 쓴다).

### 7-4. `POST /api/analyze`

- Content-Type: `multipart/form-data`
- Body: `files` (복수), `question` (선택, string)

```json
{
  "kpis": {
    "period": "2026-09",
    "previous_period": "2026-08",
    "current":  { "revenue": 12600000, "orders": 830, "units": 1020, "ad_spend": 1920000, "ad_revenue": 6000000, "roas": 312.5 },
    "previous": { "revenue": 10400000, "orders": 700, "units": 860,  "ad_spend": 1500000, "ad_revenue": 4900000, "roas": 326.7 },
    "change":   { "revenue_change": 21.2, "orders_change": 18.6, "units_change": 18.6, "ad_spend_change": 28.0, "ad_revenue_change": 22.4, "roas_change_pp": -14.2 }
  },
  "comparison": {
    "by_platform": [
      { "platform": "coupang", "revenue": 8000000, "orders": 520, "ad_spend": 1200000, "ad_revenue": 3500000, "roas": 291.7 },
      { "platform": "naver",   "revenue": 4600000, "orders": 310, "ad_spend": 720000,  "ad_revenue": 2500000, "roas": 347.2 }
    ],
    "trend": [
      { "period": "2026-08", "revenue": 10400000, "roas": 326.7 },
      { "period": "2026-09", "revenue": 12600000, "roas": 312.5 }
    ]
  },
  "rows": [ { "period": "2026-09", "platform": "coupang", "product_id": "P001", "product_name": "...", "revenue": 0, "orders": 0, "units": 0, "ad_spend": 0, "ad_revenue": 0 } ],
  "signals": [
    { "signal": "ROAS_DOWN_WITH_SPEND_GROWTH", "platform": "all", "ad_spend_change": 28.0, "ad_revenue_change": 22.4, "roas_change_pp": -14.2 }
  ],
  "insight": {
    "status": "ok",
    "plan": { "metric": "roas", "group_by": "platform", "sort": "asc" },
    "answer": [ { "platform": "coupang", "roas": 291.7 } ],
    "summary": "매출은 증가했지만 광고비 증가율이 광고매출 증가율보다 높아 ROAS가 하락했습니다.",
    "evidence": ["광고비 +28.0%", "광고매출 +22.4%", "ROAS -14.2%p"],
    "checks": ["어느 플랫폼에서 ROAS가 가장 크게 하락했는지 확인", "광고비 증가 대비 주문 증가폭 확인"],
    "actions": ["저효율 플랫폼의 광고비를 우선 점검", "예산 조정 전 최근 추이를 추가 확인"],
    "limitations": ["현재 데이터만으로 광고 소재·CTR·CPC·CVR 영향은 확인할 수 없습니다."]
  }
}
```

**필드 책임:** `kpis` / `comparison` / `rows` / `signals` → C, `insight` → D, 전체 조립 → B, 렌더링 → A

**`insight.status`:**
| 값 | 의미 | 프론트 처리 |
|---|---|---|
| `ok` | 정상 | 전체 표시 |
| `unsupported_question` | 질문을 분석 계획으로 변환 불가 | 안내 문구 + 질문 예시 표시 |
| `llm_error` | LLM 호출 실패/타임아웃/JSON 검증 실패, API 키 없음, 계획 실행(`run_plan`) 중 예상 못 한 오류 | KPI는 표시, AI 영역에 재시도 안내 |
| `skipped` | 예약된 값. 현재 서버는 **반환하지 않음** (질문이 없어도 인사이트를 생성하고, LLM 이 정할 수 있는 `status` 는 `InsightDraft` 의 `ok`·`unsupported_question` 뿐 — 8-2 참고) | AI 영역 숨김 |

- 질문이 없으면 계획(`plan`)·답(`answer`) 없이 KPI 요약 인사이트를 만든다.
- `unsupported_question` 이면 `summary` 에 사용자에게 보여 줄 이유가 담긴다 (예: 데이터에 없는 월을 물으면 업로드된 기간 안내).

## 8. AI 모듈 명세 (D)

### 8-1. Planner — 질문 → 분석 계획

```json
{
  "metric": "revenue | orders | units | ad_spend | ad_revenue | roas",
  "group_by": "platform | period | product | null",
  "sort": "asc | desc | null",
  "limit": 5,
  "period": "YYYY-MM | null"
}
```

- Pydantic 모델 `AnalysisPlan` 으로 검증, 허용되지 않은 값은 `unsupported_question`
- LLM은 계획만 만들고, 실행은 `analysis/compare.run_plan(df, plan)` 이 수행

### 8-2. Insight — 계산 결과 → 설명

- 입력: `kpis`, `comparison`, `signals`, (선택) `plan` + `answer`
- 출력: `summary`, `evidence`, `checks`, `actions`, `limitations` (Pydantic `Insight` 로 검증)
- LLM 은 `InsightDraft`(`status`, `summary`, `evidence`, `checks`, `actions`, `limitations`, `reason`)만 생성한다. `status` 는 `ok` / `unsupported_question` 만 허용된다.
- `plan`·`answer` 는 LLM 이 만들지 않고, 서버가 위에서 계산한 값을 붙여 최종 `Insight` 를 만든다 (LLM 이 계산 결과를 바꾸지 못하게 하기 위함).
- LLM 호출이 실패하면 `Insight(status="llm_error")` 를 반환한다.
- 프롬프트 규칙:
  1. 입력에 있는 숫자만 사용, 숫자 재계산·변경 금지
  2. 입력 데이터에 없는 요인(광고 소재, CTR, CPC, CVR, 경쟁사 가격, 시장 상황)을 원인으로 단정 금지 → `limitations` 에 "확인 불가 + 필요한 추가 데이터"로 기술
  3. 원인은 "후보"로 표현
  4. 한국어, 간결한 문장
- 후처리 검증: `evidence` 의 숫자가 입력 KPI 값과 일치하는지 확인, 불일치 시 해당 항목 제거

### 8-3. 실패 처리

| 상황 | 처리 |
|---|---|
| 타임아웃 (`LLM_TIMEOUT_SECONDS`, 기본 30초) | `llm_error` |
| JSON 파싱/검증 실패 | 1회 재시도 후 `llm_error` |
| API 키 없음 | `llm_error` (서버 로그에 원인 기록) |

## 9. Frontend 명세 (A)

| 화면 영역 | 구성 | 데이터 |
|---|---|---|
| Upload | 파일 선택, 파일 목록(플랫폼·기간·행 수), 미리보기 표 | `/api/preview` |
| KPI | 카드 6개 (값 + 전월 대비, 증가 녹색/감소 적색, ROAS는 %p) | `kpis` |
| Platform Compare | 막대 차트 (플랫폼별 매출·ROAS) | `comparison.by_platform` |
| Trend | 라인 차트 (기간별 매출·ROAS) | `comparison.trend` |
| Signals | 경고 배지 목록 | `signals` |
| Insight | 질문 입력, 요약, 근거 / 확인 항목 / 행동 제안 / 한계 | `insight` |

- 숫자 포맷: 금액 `12,600,000원`, 비율 `+21.2%`, ROAS 증감 `-14.2%p`
- 상태: `idle` / `uploading` / `analyzing` / `done` / `error`
- 타입: `frontend/types/` 에 API 응답 타입 정의 (`shared/contracts` 기준)

## 10. 환경변수

| 변수 | 위치 | 설명 |
|---|---|---|
| `LLM_API_KEY` | Backend | LLM API 키 (절대 커밋 금지). 현재 `ai/client.py` 는 `OPENAI_API_KEY` 를 **우선** 읽고, 없으면 `LLM_API_KEY` 를 읽음 — 하나로 통일 예정 |
| `LLM_MODEL` | Backend | 사용할 모델명 |
| `LLM_TIMEOUT_SECONDS` | Backend | LLM 호출 1회당 타임아웃(초), 기본 30 |
| `LLM_MODE` | Backend | `real` / `mock`. ⚠️ mock 은 아직 구현되지 않음 (키가 없으면 `llm_error`) |
| `ALLOWED_ORIGINS` | Backend | CORS 허용 도메인 (쉼표 구분, Vercel URL 포함) |
| `MAX_FILES` | Backend | 기본 10 |
| `MAX_FILE_SIZE_MB` | Backend | 기본 5 |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend | Backend URL |
| `NEXT_PUBLIC_USE_MOCK` | Frontend | `true` 면 Backend 대신 mock 데이터 사용 |
| `PYTHON_VERSION` | Render | 백엔드 Python 버전 고정 (`3.12.10`) |

각 앱에 `.env.example` 을 커밋하고 실제 `.env` 는 `.gitignore` 에 포함한다.

## 11. 배포

| 대상 | 플랫폼 | 설정 |
|---|---|---|
| Frontend | Vercel | Root: `frontend/`, env: `NEXT_PUBLIC_API_BASE_URL` |
| Backend | Render (Web Service) | Root: `backend/`, Build: `pip install -r requirements.txt`, Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |

**배포 주소**

| 대상 | URL |
|---|---|
| Backend (Render) | https://seller-insight-api-31fd.onrender.com (`/health`, `/docs`) |
| Frontend (Vercel) | https://ai-seller-insight.vercel.app |

**Render 설정 (실제 적용값)**
- Region: Singapore, Instance: Free
- Health Check Path: `/health`
- 환경변수: `PYTHON_VERSION=3.12.10`, `ALLOWED_ORIGINS`, `LLM_MODE` (API 키는 Render 대시보드에서만 입력)
- 저장소를 Public Git Repository 로 연결해 Render 자체 자동 배포는 동작하지 않음 → GitHub Actions(`.github/workflows/render-deploy.yml`)가 `main` 에 `backend/` 변경이 push 되면 Render **Deploy Hook** 을 호출해 재배포 (URL 은 저장소 Secret `RENDER_DEPLOY_HOOK_URL`)
- Actions 가 실패하거나 즉시 반영이 필요하면 Actions 탭에서 **Run workflow** 또는 Render 에서 **Manual Deploy → Deploy latest commit**

- Render 무료 플랜 콜드 스타트 대비: 시연 전 `/health` 호출로 워밍업 (첫 요청 최대 50초 이상 지연 가능)

## 12. 테스트 전략

| 레벨 | 담당 | 내용 |
|---|---|---|
| 단위 (analysis) | C | fixture 입력 → KPI·비교·신호 정답 비교 |
| 단위 (ai) | D | 질문 세트 → 계획 JSON 검증, 숫자 불변·과잉 추론 금지 검증, LLM 실패 모킹 |
| API | B | 정상/실패 케이스별 상태코드·오류 코드 확인 |
| 통합 (E2E) | 전원 | 배포 환경에서 업로드 → KPI → 질문 → 인사이트 |

**실패 테스트 케이스:** 빈 파일, 누락 컬럼, 잘못된 숫자, LLM 장애, 잘못된 질문, 파일 크기 초과, 파일 개수 초과, 미지원 확장자

## 13. Git 규칙

- Branch: `feat/<영역>-<내용>`, `fix/<영역>-<내용>` (예: `feat/fe-upload`, `feat/data-kpi`)
- Commit: `feat:`, `fix:`, `docs:`, `test:`, `refactor:` 접두사
- PR: 작게, 리뷰어 1명 승인 후 Merge (A→B, B→C, C→D, D→A)
- `shared/contracts/` 변경 PR은 전원 확인
