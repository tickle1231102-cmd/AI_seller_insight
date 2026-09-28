# Seller Insight AI — 4인 역할 분담 및 협업 가이드

> **목표:** 4명이 같은 GitHub 저장소에서 충돌을 최소화하면서 멀티플랫폼 판매·광고 데이터를 통합 분석하는 MVP를 완성한다.

---

## 1. 프로젝트 한 줄 정리

여러 판매·광고 플랫폼에서 내려받은 Excel/CSV 데이터를 통합하고, 매출·주문·광고비·광고매출·ROAS 등의 KPI를 계산해 플랫폼별·기간별 성과를 비교하고 AI가 **데이터 기반 원인 후보와 다음 행동을 제안**하는 서비스.

---

## 2. 전체 기술 스택

| 영역 | 기술 | 역할 |
|---|---|---|
| Frontend | Next.js + React + TypeScript | 파일 업로드, KPI 대시보드, AI 분석 결과 화면 |
| Chart | Recharts | 매출·주문·ROAS·플랫폼별 비교 및 추이 |
| Backend | Python + FastAPI | 파일 수신, 요청 처리, 분석 모듈 연결, 결과 반환 |
| Data Validation | Pydantic | API 요청·응답, AI 분석 JSON 검증 |
| Data Analysis | pandas | 데이터 통합, KPI 계산, 비교 분석 |
| Excel | openpyxl | XLSX 파일 직접 읽기 필요 시 사용 |
| AI | LLM API | 자연어 질문 → 분석 계획 JSON, KPI 해석·행동 제안 |
| Frontend Deploy | Vercel | Next.js 배포 |
| Backend Deploy | Render | FastAPI 서버 호스팅 |
| DB | MVP 제외 | 추후 저장/로그인 기능 시 Supabase 검토 |
| Collaboration | GitHub Collaborators + Branch + PR | 4명 공동 개발 및 리뷰 |

---

## 3. 4명 역할 분담

### A — Frontend / UI

**핵심 책임:** 사용자가 실제로 보는 화면 전체 담당.

#### 구현 항목
- 다중 Excel/CSV 업로드 UI
- 업로드 파일 목록
- 데이터 미리보기
- 플랫폼·기간 표시
- 전체 KPI 화면
  - 매출
  - 주문
  - 광고비
  - 광고매출
  - ROAS
- 전월 대비 변화 표시
- 쿠팡 vs 네이버 등 플랫폼 비교
- 매출·ROAS 추이 차트
- 자연어 질문 입력
- AI 분석 결과 표시
- AI 확인 항목 / 행동 제안 UI
- 로딩 / 오류 화면
- 반응형 화면

#### 사용 기술

```text
Next.js
React
TypeScript
Recharts
```

#### 담당 영역

```text
frontend/
├─ app/
├─ components/
├─ features/
│  ├─ upload/
│  ├─ dashboard/
│  └─ insight/
├─ lib/api/
└─ types/
```

#### A가 하지 않는 것
- pandas 계산
- ROAS 공식 구현
- FastAPI 내부 로직
- LLM 호출 구현

#### 완료 기준

> 실제 FastAPI 응답을 받아 KPI·표·차트·AI 설명이 화면에 정상 표시된다.

**기본 검토자: B**

---

### B — Backend / API / 통합 / 배포

**핵심 책임:** Frontend와 Data/AI 기능을 연결하는 중심 역할.

#### 구현 항목
- FastAPI 서버
- 파일 업로드 API
- `/health`
- `/api/preview`
- `/api/analyze`
- 파일 개수·크기 검증
- 질문 길이 검증
- Pydantic 요청/응답 검증
- C 데이터 분석 모듈 호출
- D AI 모듈 호출
- 오류 처리
- CORS 설정
- 환경변수 관리
- Render Backend 배포
- Vercel ↔ Render 연결

#### 구조

```text
Frontend
   ↓
FastAPI
   ├── C 데이터 분석
   └── D AI 분석
   ↓
JSON Response
   ↓
Frontend
```

#### 담당 영역

```text
backend/app/
├─ main.py
├─ schemas.py
├─ routers/
└─ core/
```

#### B가 하지 않는 것
- KPI 계산 공식 작성
- pandas 내부 계산 로직
- AI 프롬프트 품질 설계
- 프론트 UI 구현

#### 완료 기준

> Frontend 요청이 FastAPI를 거쳐 C와 D 모듈을 호출하고 정상 JSON으로 반환된다.

**기본 검토자: C**

---

### C — Data Analysis / pandas / QA

**핵심 책임:** 실제 데이터 처리와 계산 기준 담당.

#### 플랫폼 데이터 정규화

쿠팡:

```text
총매출
주문
판매량
광고비
광고매출
```

네이버:

```text
판매금액(순)
상품결제건수
결제상품수량
광고비용
전환매출
```

↓ 공통 구조

```text
period
platform
product_id
product_name
revenue
orders
units
ad_spend
ad_revenue
```

#### KPI 계산

```text
전체 매출
전체 주문
판매량
광고비
광고 전환매출
ROAS
전월 대비 매출 증감
전월 대비 주문 증감
전월 대비 광고비 증감
ROAS 증감
```

ROAS:

```text
ROAS = 광고 전환매출 ÷ 광고비 × 100
```

#### 비교 분석 예

```text
8월
매출      10,400,000원
광고비     1,500,000원
ROAS            326.7%

9월
매출      12,600,000원
광고비     1,920,000원
ROAS            312.5%
```

↓

```text
매출      +21.2%
광고비    +28.0%
ROAS      -14.2%p
```

#### 이상 신호 계산

```json
{
  "signal": "ROAS_DOWN_WITH_SPEND_GROWTH",
  "ad_spend_change": 28.0,
  "ad_revenue_change": 22.4,
  "roas_change_pp": -14.2
}
```

AI는 이 계산 결과를 설명만 한다.

#### 사용 기술

```text
Python
pandas
openpyxl
```

#### 담당 영역

```text
backend/app/analysis/
├─ normalize.py
├─ kpi.py
├─ compare.py
└─ signals.py

shared/fixtures/
```

#### 완료 기준

> 같은 입력 데이터에 대해 항상 같은 KPI와 정답이 나온다.

**기본 검토자: D**

---

### D — AI / Insight / AI QA

**핵심 책임:** AI가 질문을 분석 명령으로 변환하고, 계산된 KPI를 사람이 이해하기 쉽게 설명하도록 만든다.

#### AI 역할 ① 질문 해석

사용자:

```text
광고 효율이 가장 안 좋은 플랫폼 어디야?
```

↓

AI:

```json
{
  "metric": "roas",
  "group_by": "platform",
  "sort": "asc"
}
```

실제 계산은 C의 pandas 코드가 수행한다.

#### AI 역할 ② KPI 해석

C 계산 결과:

```text
매출        +21.2%
광고비      +28.0%
광고매출    +22.4%
ROAS        -14.2%p
```

↓

AI:

```text
매출은 증가했지만 광고비 증가율이
광고매출 증가율보다 높아 ROAS가 하락했습니다.
```

#### AI 역할 ③ 확인 항목·행동 제안

확인할 항목:
- 어느 플랫폼에서 ROAS가 가장 크게 하락했는지 확인
- 광고비 증가 대비 주문 증가폭 확인
- 최근 1~2주 추이 확인

행동 제안:
- 저효율 플랫폼의 광고비를 우선 점검
- 효율이 높은 플랫폼과 비교
- 예산 조정 전 최근 추이를 추가 확인

#### AI 과잉 추론 방지

현재 데이터에 없는 내용:

```text
광고 소재
CTR
CPC
CVR
경쟁사 가격
시장 상황
```

이런 데이터가 없는데 AI가:

> 광고 소재가 안 좋아서 ROAS가 떨어졌습니다.

라고 말하면 실패.

대신:

> 현재 데이터만으로 광고 소재 영향을 확인할 수 없습니다. CTR·CPC·CVR 데이터를 추가 확인하는 것이 좋습니다.

처럼 표현해야 한다.

#### 담당 영역

```text
backend/app/ai/
├─ planner.py
├─ insight.py
└─ prompts/

backend/tests/test_ai.py
```

#### 완료 기준
- 자연어 질문 → 올바른 분석 JSON
- 계산된 숫자를 임의 변경하지 않음
- 데이터에 없는 원인을 단정하지 않음
- LLM 실패 처리
- 근거 / 확인 항목 / 행동 제안 분리

**기본 검토자: A**

---

## 4. 역할별 파일 충돌 최소화 구조

```text
seller-insight-ai/

├─ frontend/                  ← A
│
├─ backend/
│  └─ app/
│     ├─ main.py              ← B
│     ├─ schemas.py           ← B
│     ├─ routers/             ← B
│     ├─ core/                ← B
│     │
│     ├─ analysis/            ← C
│     │  ├─ normalize.py
│     │  ├─ kpi.py
│     │  ├─ compare.py
│     │  └─ signals.py
│     │
│     └─ ai/                  ← D
│        ├─ planner.py
│        ├─ insight.py
│        └─ prompts/
│
├─ shared/
│  ├─ contracts/              ← 전원 합의 / B 관리
│  └─ fixtures/               ← C
│
└─ DevelopDoc/
```

핵심은 **각자 다른 폴더를 주로 수정하는 것**이다.

---

## 5. 문서 분담

| 문서 | 주 담당 |
|---|---|
| README | B |
| PRD | A + D |
| TECH_SPEC | B |
| WORK_UNITS | 전원 / B 정리 |
| FINAL_CHECKLIST | D |
| 테스트 결과 | C + D |
| 역할분담 / 일정 | A |
| AI 활용 사례 | D |

원칙:

> 자기 구현 부분은 자기가 작성하고, 마지막에 한 사람이 형식만 정리한다.

---

## 6. GitHub 협업 방식

### 저장소

GitHub Repository는 **1개**만 사용.

```text
Repository Owner 1명
+
Collaborator 3명
```

전원 같은 저장소 Clone.

### 작업 흐름

```text
main 최신화
    ↓
작업 Branch 생성
    ↓
개발
    ↓
테스트
    ↓
Commit
    ↓
Push
    ↓
Pull Request
    ↓
다른 팀원 Review
    ↓
Merge
    ↓
최신 main 통합 테스트
```

### 리뷰 순서

```text
A → B 리뷰
B → C 리뷰
C → D 리뷰
D → A 리뷰
```

자기 PR을 자기가 승인하지 않는다.

---

## 7. 반드시 먼저 합의할 공통 계약

### 7-1. 공통 데이터 구조

```text
period
platform
product_id
product_name
revenue
orders
units
ad_spend
ad_revenue
```

이 구조가 바뀌면 전원이 영향을 받기 때문에 개인이 임의 변경하지 않는다.

### 7-2. API 응답 구조

```json
{
  "kpis": {},
  "comparison": {},
  "rows": [],
  "signals": [],
  "insight": {}
}
```

역할 관계:

```text
C
→ kpis / comparison / rows / signals

D
→ insight

B
→ 전체 JSON 조립 및 API 반환

A
→ JSON을 화면에 표시
```

이 계약이 고정되면 4명이 동시에 개발할 수 있다.

---

## 8. 5일 작업 순서

### Day 1 — 기획·공통 기반

```text
기획 확정
↓
공통 데이터 구조 확정
↓
API JSON 확정
↓
GitHub 저장소 생성
↓
Collaborator 초대
↓
공통 프로젝트 뼈대 생성
```

완료 기준:
- 전원이 같은 저장소 Clone
- 최소 Next.js 화면 실행
- FastAPI `/health` 실행
- Branch → PR → Merge 한 번 경험

### Day 2 — 담당별 개발

A:
```text
파일 업로드
대시보드 UI
KPI 화면
```

B:
```text
FastAPI
파일 업로드 API
Pydantic
```

C:
```text
쿠팡/네이버 데이터 정규화
KPI 계산
```

D:
```text
LLM
자연어 질문 → JSON
```

### Day 3 — 기능 확장·연결

A:
```text
실제 API 연결
차트
AI 결과 UI
```

B:
```text
C 데이터 모듈 연결
D AI 모듈 연결
```

C:
```text
전월 비교
플랫폼 비교
이상 신호
```

D:
```text
KPI 설명
원인 후보
확인 항목
행동 제안
```

### Day 4 — 전체 통합·검증

```text
Frontend
   ↓
FastAPI
   ↓
pandas
   ↓
LLM
   ↓
Frontend
```

실패 테스트:

```text
빈 파일
누락 컬럼
잘못된 숫자
LLM 장애
잘못된 질문
파일 크기 초과
```

### Day 5 — 제출

새 기능 추가 중단.

```text
버그 수정
↓
최종 배포
↓
README/문서
↓
발표 자료
↓
시연
↓
제출
```

---

## 9. 업무량 균형

- **A:** 화면 구현량이 많음
- **B:** 전체 연결과 배포 난도가 높음
- **C:** 데이터 처리·테스트 작업량이 많음
- **D:** LLM 프롬프트·AI 품질·검증 작업량이 많음

특정 한 명이 발표·문서만 맡는 구조보다 **4명 모두 실제 구현에 참여하는 구조**로 운영한다.

---

## 10. 최종 한눈 요약

```text
A · Frontend
Next.js / UI / Recharts
        │
        ▼
B · Backend
FastAPI / API / Pydantic / 배포
        │
    ┌───┴────┐
    ▼        ▼
C · Data     D · AI
pandas       LLM API
KPI          질문 해석
정규화       KPI 설명
비교         행동 제안
    │        │
    └───┬────┘
        ▼
     B 통합
        ↓
     A 화면
```

---

## 11. 핵심 협업 원칙

1. **Repository는 하나**
2. **4명 모두 Collaborator**
3. **main 직접 수정 금지**
4. **작업별 Branch**
5. **작은 Pull Request**
6. **다른 팀원이 Review**
7. **API·공통 데이터 구조는 개인이 임의 변경하지 않음**
8. **AI가 만든 코드도 직접 실행·검증**
9. **마지막 날 한꺼번에 Merge하지 않음**
10. **매일 최신 main으로 전체 흐름 확인**

> **목표는 각자 자기 파트를 만드는 것이 아니라, 네 명의 코드가 매일 하나의 서비스로 연결되는 것입니다.**
