# 테스트 결과 (WU-DA-06 · C 작성 초안, D 항목은 D 가 채움)

- 작성: 2026-09-30, C
- 기준 커밋: `origin/main` `1804e16` + 이 브랜치의 변경(`UNREADABLE_FILE` 추가, `test_failure_cases.py`)
- 방법: 백엔드 `pytest`, 합성 fixture(`shared/fixtures/`)로 로컬·배포 서버(Render) 호출. 실제 판매 데이터는 쓰지 않았다.

## 1. 자동 테스트

| 항목 | 결과 |
|---|---|
| `backend` 전체 `pytest` | 185 통과 · 1 건너뜀(`test_ai_live`, 실제 LLM 키가 있을 때만 실행) |
| 이 브랜치가 추가한 테스트 | `tests/test_failure_cases.py` 31개 (실패 7종 × preview·analyze 양쪽, 경계값, 손상 파일, 일부 파일만 나쁜 경우) |

## 2. 실패 케이스 (WU-DA-06 완료 조건 1·2)

`/api/preview` 와 `/api/analyze` 양쪽에서 같은 결과. 로컬 = `pytest`, 배포 = Render 서버에 같은 파일을 직접 전송.

| # | 케이스 | 입력 | HTTP | 오류 코드 | 로컬 | 배포 |
|---|---|---|---|---|---|---|
| 1 | 빈 파일 | 헤더만 있는 CSV | 422 | `EMPTY_FILE` | ✅ | ✅ |
| 2 | 누락 컬럼 | `광고매출` 컬럼 없음 | 422 | `MISSING_COLUMNS` (`missing: ["광고매출"]`) | ✅ | ✅ |
| 3 | 잘못된 숫자 | 2행 `총매출` = `abc` | 422 | `INVALID_NUMBER` (`row: 2`, `column: 총매출`) | ✅ | ✅ |
| 4 | 파일 크기 초과 | 5MB + 1바이트 | 413 | `FILE_TOO_LARGE` | ✅ | ✅ |
| 5 | 파일 개수 초과 | 11개 | 400 | `TOO_MANY_FILES` | ✅ | ✅ |
| 6 | 미지원 확장자 | `report.pdf` | 400 | `UNSUPPORTED_FILE_TYPE` | ✅ | ✅ |
| 7 | 미지원 플랫폼 | 쿠팡·네이버 컬럼 아님 | 422 | `UNKNOWN_PLATFORM` | ✅ | ✅ |
| 추가 | 손상된 파일 | zip 이 아닌 `.xlsx`, 인코딩 불명 CSV | 422 | `UNREADABLE_FILE` (신규) | ✅ | ❌ 500 (수정 전 코드, 재배포 필요) |

경계값(모두 통과): 파일 10개 정확히 → 통과, 5MB 정확히 → 크기 오류 아님, 확장자 대소문자 무시(`.CSV`), `.xls`·확장자 없음·`.csv.exe`·`.csv␠` 는 거절.
여러 파일 중 하나만 나쁘면 요청 전체가 그 파일의 오류 코드로 실패하고 `details.file` 에 그 파일명이 들어간다. 확장자 오류는 내용 오류보다 먼저 보고된다.

### 이번 QA 에서 찾아 고친 문제
- **손상된 `.xlsx` / 해독 불가 CSV 가 500 `INTERNAL_ERROR` 로 응답** → `normalize._read_table` 에서 잡아 `UNREADABLE_FILE`(422, `details.file`)로 변경. `shared/contracts/README.md`·`TECH_SPEC.md` 오류 표에 추가.
- 프론트 `client.ts` 의 `MESSAGES` 에는 아직 이 코드가 없다. 서버 message 를 대신 보여주므로 화면은 동작하지만, 프론트도 같은 문구 체계를 원하면 A 가 한 줄 추가하면 된다.

## 3. 화면 메시지 (완료 조건 3)

- 미확인. Vercel 프론트가 `NEXT_PUBLIC_API_BASE_URL` 미설정으로 mock 모드라 실제 서버 오류가 화면에 나오지 않는다. 설정 후 위 8종을 화면에서 1회씩 확인해 결과를 여기에 적는다.
- 코드 확인만 한 것: `client.ts` 의 `MESSAGES` 가 7종 모두(`FILE_TOO_LARGE`, `TOO_MANY_FILES`, `UNSUPPORTED_FILE_TYPE`, `EMPTY_FILE`, `MISSING_COLUMNS`, `INVALID_NUMBER`, `UNKNOWN_PLATFORM`)에 대해 파일명·행 번호를 포함한 문구를 갖고 있고, 업로드 전 `validateFiles` 가 개수·확장자·크기를 브라우저에서 먼저 막는다.

## 4. KPI 수기 검산 (완료 조건 4)

- 합성 fixture 기준: 쿠팡 2026-09 합계를 손으로 더해 `expected_kpis.json` 과 대조 — 매출 8,000,000 · 주문 520 · 광고비 1,200,000 · 광고매출 3,500,000 · ROAS 291.7 % 일치. 전체 KPI 는 `test_analysis.py` 가 정답 파일과 비교하고, 배포 서버 `/api/analyze` 결과도 정답과 일치(9/29 확인).
- **미충족:** "실제 형식에 가까운 샘플"로는 하지 못했다. 현재 fixture 는 전부 합성이라 `PLATFORM_COLUMN_MAP` 의 컬럼명이 실제 쿠팡·네이버 내보내기와 맞는지 검증되지 않았다. 실제 형식 샘플 확보 후 재검산 필요.

## 5. 시연용 파일

- 정상·실패 fixture 는 모두 7KB 이하(5MB 한도와 무관).
- 파일 크기 초과 시연용: `coupang_2026-09_too_large.csv` (5,243,942바이트, 저장소 밖 `C:\Users\alshf\demo_fixtures\`). 용량 때문에 저장소에는 넣지 않고, 필요하면 `test_failure_cases.py::oversized_csv` 와 같은 방식으로 다시 만든다.

## 6. AI 인사이트 · 질문 (D 가 채움)

- (D) 과잉 추론 방지·숫자 규칙 테스트 결과
- (C) Luna 실측 요약(9/29, `main`+#12): 질문 해석 14/14, 인사이트 5/5 성공·숫자 규칙 차단 0건, 응답 30초 안팎. #18 이 머지되면 구조가 바뀌므로 재측정 후 갱신.
