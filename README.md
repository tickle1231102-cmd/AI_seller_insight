# Seller Insight AI

> 여러 판매·광고 플랫폼 데이터를 한 번에 올리면, KPI를 계산하고 AI가 **데이터 기반 원인 후보와 다음 행동**을 제안하는 셀러용 분석 서비스

---

## 배포

| 대상 | URL |
|---|---|
| Frontend (Vercel) | https://ai-seller-insight.vercel.app |
| Backend API (Render) | https://seller-insight-api-31fd.onrender.com |
| API 문서 (Swagger) | https://seller-insight-api-31fd.onrender.com/docs |

> Render 무료 플랜은 한동안 요청이 없으면 잠듭니다. 첫 요청이 50초 이상 걸릴 수 있으니 시연 전에 [`/health`](https://seller-insight-api-31fd.onrender.com/health) 를 한 번 열어 깨워 두세요.

## 무엇을 해결하나요?

온라인 셀러는 쿠팡, 네이버 등 여러 플랫폼에서 판매·광고 데이터를 따로 내려받아 엑셀로 직접 합치고 계산합니다.
플랫폼마다 컬럼 이름이 다르고, ROAS 같은 지표를 매번 손으로 계산해야 하며, "왜 떨어졌는지"는 감으로 판단하는 경우가 많습니다.

**Seller Insight AI**는 이 과정을 자동화합니다.

1. 플랫폼별 Excel/CSV 파일을 여러 개 업로드
2. 공통 구조로 자동 정규화
3. 매출·주문·광고비·광고매출·ROAS 등 KPI 자동 계산
4. 전월 대비 변화 및 플랫폼별 비교
5. 자연어로 질문하면 AI가 분석하고, 계산된 숫자를 근거로 **확인할 항목과 행동 제안**을 제시

## 주요 기능

| 기능 | 설명 |
|---|---|
| 다중 파일 업로드 | 쿠팡·네이버 템플릿, 쿠팡·네이버 실제 내보내기, 스마트스토어 판매 분석 Excel/CSV 파일 여러 개 동시 업로드 및 미리보기 ([지원 입력](#지원-입력)) |
| 데이터 정규화 | 플랫폼별 상이한 컬럼을 공통 스키마로 통합 |
| KPI 대시보드 | 매출, 주문, 판매량, 광고비, 광고매출, ROAS |
| 기간 비교 | 전월 대비 매출·주문·광고비 증감률, ROAS 증감(%p) |
| 플랫폼 비교 | 쿠팡 vs 네이버 등 플랫폼별 성과 비교 차트 |
| 이상 신호 감지 | 예: 광고비는 늘었는데 ROAS가 하락 (`ROAS_DOWN_WITH_SPEND_GROWTH`) |
| AI 질문 분석 | "광고 효율이 가장 안 좋은 플랫폼 어디야?" → 분석 계획 JSON → pandas 계산 |
| AI 인사이트 | 근거 / 확인 항목 / 행동 제안을 분리해 제시, 데이터에 없는 원인은 단정하지 않음 |

## 지원 입력

판별은 파일명이 아니라 **컬럼 구조**로 해요 (기준: `backend/app/analysis/normalize.py`).

**플랫폼 실제 내보내기 파일**

| 파일 | 알아보는 컬럼 | 들어가는 값 | 기간 |
|---|---|---|---|
| 쿠팡 판매 지표 (Wing › 판매 분석 › 옵션별) | `옵션 ID`·`등록상품ID`·`매출(원)` | 매출(`매출(원)`)·주문·판매량 | 파일 안에 없음 → 파일명의 `YYYY-MM` 또는 날짜 범위(가운데 월, 예: `_20260830-20260928` → 2026-09), 둘 다 없으면 **화면에서 월 입력** |
| 쿠팡 광고 리포트 | `캠페인 ID`·`광고집행 옵션ID`·`광고비` | 광고비·광고매출(**`총 전환매출액(14일)`**) | 위와 같음 |
| 네이버 쇼핑검색광고 소재 보고서 | `일별`·`소재`·`총비용` | 광고비(`총비용`)·광고매출(`총 전환매출액`) | `일별` 컬럼 |
| 네이버 스마트스토어 판매 분석(SALES) | `채널상품번호`·`채널상품명`·`판매금액(총)` | 매출(`판매금액(순)`)·주문·수량 + 방문수·환불·할인 | 행의 `날짜`, 없으면 파일명 |

**팀 정의 통합 템플릿**

| 템플릿 | 필요한 컬럼 | 기간 |
|---|---|---|
| 쿠팡 | `상품ID`, `상품명`, `총매출`, `주문`, `판매량`, `광고비`, `광고매출` | 파일명의 `YYYY-MM` (예: `coupang_2026-09.csv`), 없으면 파일명의 날짜 범위 (예: `_20260901-20260930`) |
| 네이버 | `상품ID`, `상품명`, `판매금액(순)`, `상품결제건수`, `결제상품수량`, `광고비용`, `전환매출` | 위와 같음 |

**합치는 방식**
- 판매 파일과 광고 파일은 **플랫폼·월 단위로 합쳐요.** 파일에 없는 지표는 0이에요 (예: 판매 파일의 광고비).
- 판매·광고 파일의 상품 ID가 달라 **상품 단위로는 합쳐지지 않아요.** "상품별 ROAS"는 정확하지 않아요.
- 스마트스토어 판매 + 네이버 광고 리포트는 `naver` 로 합쳐 KPI를 계산해요. 같은 월에 판매 수치가 있는 **네이버 템플릿**도 함께 올리면 판매액이 겹쳐서, 그 월의 스마트스토어 행은 KPI에서 빼요.

**파일 조건**
- `.xlsx`(첫 번째 시트) 또는 `.csv`(UTF-8·BOM 포함 UTF-8·CP949). 최대 10개, 파일당 5MB. `.xls`·`.tsv`·`.txt` 등 다른 확장자는 `UNSUPPORTED_FILE_TYPE` 이에요.
- 날짜 범위가 두 달에 걸치면 범위의 가운데 날짜가 속한 월로 봐요 (예: `20260830-20260928` → 2026-09).
- 컬럼은 이름으로 찾아서 순서는 상관없어요. 숫자 빈 셀은 0, 분모가 0인 지표(광고비 0일 때 ROAS 등)는 0이 아니라 값 없음(`null`)이에요.
- 셀 값 `-` 는 스마트스토어 판매 파일에서만 0으로 봐요 (다른 파일은 `INVALID_NUMBER`). 스마트스토어의 `전체` 합계 행은 같은 월에 상품 행이 있으면 자동으로 빼요 (중복 집계 방지).
- 예시 파일: `shared/fixtures/` (팀 템플릿), `shared/fixtures/smartstore/` (스마트스토어 판매 분석), `shared/fixtures/exports/` (실제 내보내기 형식 샘플).

**지원하지 않는 입력**
- 위 표에 없는 형식 → `UNKNOWN_PLATFORM`. 지표 컬럼이 3개 이상 겹치지만 일부가 빠진 템플릿은 `MISSING_COLUMNS` 로 나와요.
- 스마트스토어 방문·검색어·고객 분석 파일 → `UNSUPPORTED_DATASET`.
- 기간 정보가 없는 파일인데 월을 입력하지 않으면 → `INVALID_PERIOD` (`details.needs_input: true`). **서버는 기간을 추정하지 않아요.**
- 판매·광고의 상품 단위 병합 (향후 과제 [#32](https://github.com/tickle1231102-cmd/AI_seller_insight/issues/32)).
- ⚠️ 같은 내용의 파일을 이름만 바꿔 두 번 올리면 숫자가 **두 배**가 돼요 (팀 템플릿은 행이 두 번 들어가고, 실제 내보내기는 같은 월·상품 행이 합쳐져요). 같은 파일은 한 번만 올려 주세요.
- 실제 형식 샘플은 공식 도움말·화면 지표를 바탕으로 만든 **합성 샘플**이라, 실제 내보내기 파일과 완전히 같다는 보장은 없어요 (검산: [`DevelopDoc/TEST_RESULTS.md`](DevelopDoc/TEST_RESULTS.md) 4장, #38·#40).

## 핵심 원칙: 계산은 코드가, 설명은 AI가

```text
숫자 계산  → pandas (결정적, 재현 가능)
질문 해석  → LLM (자연어 → 분석 계획 JSON)
결과 설명  → LLM (계산된 숫자를 변경하지 않고 해석만)
```

AI는 CTR·CPC·광고 소재·경쟁사 가격처럼 **업로드 데이터에 없는 요인**을 원인으로 단정하지 않고, 추가로 확인할 데이터를 안내합니다.

복합 상품 진단도 지원합니다. 동일 상품의 기준 월과 전월 자료를 올리고 “저평가된 상품은?”, “관리할 상품 3개”, “광고비는 늘었는데 성과가 떨어진 상품”처럼 물어보면, 서버가 계산한 **기회 후보·관리 후보와 근거**를 보여줍니다. 이 진단 경로는 정해진 질문 규칙·점수·문구를 사용하므로 LLM 호출이 추가되지 않습니다. 시장가치·마진·재고를 추정하지 않으며, [계산 기준과 지원 범위](DevelopDoc/PRODUCT_DIAGNOSIS.md)를 확인할 수 있습니다.

## 아키텍처

```text
[Next.js Frontend (Vercel)]
          │  파일 업로드 / 질문
          ▼
[FastAPI Backend (Render)]
     ├── analysis/  (pandas: 정규화 · KPI · 비교 · 이상 신호)
     └── ai/        (LLM: 질문 해석 · 인사이트 생성)
          │  JSON { kpis, comparison, rows, signals, insight }
          ▼
[Next.js Frontend] KPI 카드 · 차트 · AI 인사이트
```

## 기술 스택

| 영역 | 기술 |
|---|---|
| Frontend | Next.js, React, TypeScript, Recharts |
| Backend | Python, FastAPI, Pydantic |
| Data | pandas, openpyxl |
| AI | LLM API |
| Deploy | Vercel (Frontend), Render (Backend) |
| DB | MVP 범위 제외 (추후 Supabase 검토) |

## 프로젝트 구조

```text
.
├─ frontend/            # Next.js 앱 (업로드, 대시보드, 인사이트 UI)
├─ backend/
│  ├─ app/
│  │  ├─ main.py        # FastAPI 진입점
│  │  ├─ schemas.py     # Pydantic 요청/응답 스키마
│  │  ├─ routers/       # /health, /api/preview, /api/analyze
│  │  ├─ core/          # 설정, 환경변수, 오류 처리
│  │  ├─ analysis/      # normalize, kpi, compare, signals
│  │  └─ ai/            # planner, insight, prompts/
│  └─ tests/
├─ shared/
│  ├─ contracts/        # 공통 데이터 구조 · API 계약
│  └─ fixtures/         # 테스트용 샘플 데이터
└─ DevelopDoc/          # 개발 문서
```

## 시작하기

### Backend

Mac / Linux

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # LLM_API_KEY 등 설정
uvicorn app.main:app --reload --port 8000
```

Windows (PowerShell)

```powershell
cd backend
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # LLM_API_KEY 등 설정
uvicorn app.main:app --reload --port 8000
```

- `http://localhost:8000/health` 에서 `{"status":"ok"}` 확인
- `http://localhost:8000/docs` 에서 API 직접 테스트 (Swagger)

테스트

```bash
cd backend
pytest -q
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # Windows: copy .env.example .env.local
                             # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

`http://localhost:3000` 접속

## API 요약

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/health` | 서버 상태 확인 |
| POST | `/api/preview` | 업로드 파일 파싱 및 미리보기 반환 |
| POST | `/api/analyze` | 파일 + 질문 → KPI · 비교 · 신호 · AI 인사이트 반환 |

상세 명세는 [TECH_SPEC.md](DevelopDoc/TECH_SPEC.md) 참고.

## 팀 구성

| 역할 | 담당 | 주요 영역 |
|---|---|---|
| A | Frontend / UI | `frontend/` |
| B | Backend / API / 통합 / 배포 | `backend/app/main.py`, `schemas.py`, `routers/`, `core/` |
| C | Data Analysis / QA | `backend/app/analysis/`, `shared/fixtures/` |
| D | AI / Insight / AI QA | `backend/app/ai/`, `backend/tests/test_ai.py` |

## 개발 문서

| 문서 | 내용 |
|---|---|
| [PRD.md](DevelopDoc/PRD.md) | 제품 요구 사항 |
| [TECH_SPEC.md](DevelopDoc/TECH_SPEC.md) | 기술 명세 (아키텍처, 데이터 스키마, API) |
| [WORK_UNITS.md](DevelopDoc/WORK_UNITS.md) | 단위 작업 명세 및 작업별 완료 조건 |
| [FINAL_CHECKLIST.md](DevelopDoc/FINAL_CHECKLIST.md) | 프로젝트 최종 완료 체크리스트 |

## 협업 규칙

- `main` 직접 수정 금지 → 작업별 Branch → PR → 다른 팀원 리뷰 → Merge
- 리뷰 순서: A → B, B → C, C → D, D → A (자기 PR 자기 승인 금지)
- 공통 데이터 구조와 API 계약(`shared/contracts/`)은 전원 합의 없이 변경하지 않음
- AI가 만든 코드도 직접 실행·검증
- 매일 최신 `main`으로 전체 흐름 확인
