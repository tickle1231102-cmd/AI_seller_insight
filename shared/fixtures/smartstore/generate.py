"""네이버 스마트스토어 통계 내보내기(판매·방문·검색·고객 분석) 형식의 샘플 픽스처 생성기.

실행: python shared/fixtures/smartstore/generate.py  (같은 폴더에 xlsx 8개 생성)

컬럼·시트명은 실제 내보내기 파일과 동일하다. 값은 고정 시드로 만든 가짜 데이터이며,
대시보드 신호가 보이도록 9월에 다음 패턴을 의도적으로 넣었다.
- 방문수 +18% 인데 결제건수는 거의 그대로 → 전환율 하락
- P1003(블루투스 스피커) 환불률 3% → 20% 급증
- 전체 할인율 5% → 9% 상승 (할인 의존)
- 검색어 '무선 이어폰' 방문 급증 + 전환 하락, 유입경로 '네이버쇼핑>검색' 전환 하락
"""

import random
from pathlib import Path

import pandas as pd

OUT = Path(__file__).parent
MONTHS = {"2026-08": ("20260801", "20260831", "2026-08-01~2026-08-31"), "2026-09": ("20260901", "20260930", "2026-09-01~2026-09-30")}

# (상품번호, 상품명, 단가, 8월 방문수, 8월 전환율%)
PRODUCTS = [
    ("P1001", "무선 이어폰", 39000, 9000, 4.2),
    ("P1002", "보조배터리 20000mAh", 29000, 6500, 5.0),
    ("P1003", "블루투스 스피커", 59000, 4200, 3.1),
    ("P1004", "C타입 고속 충전기", 15000, 7800, 6.3),
    ("P1005", "스마트워치 스트랩", 12000, 3900, 4.8),
    ("P1006", "노트북 파우치", 22000, 2600, 3.9),
    ("P1007", "무선 마우스", 25000, 5100, 4.5),
    ("P1008", "기계식 키보드", 89000, 3300, 2.2),
    ("P1009", "USB 허브 7포트", 32000, 2100, 3.6),
    ("P1010", "휴대폰 거치대", 9900, 4700, 7.1),
]

SALES_COLUMNS = [
    "날짜 기준", "날짜", "채널상품명", "채널상품번호", "상품결제건수", "환불건수", "환불건수비율", "판매금액(총)", "판매금액(순)",
    "상품결제단가", "환불금액", "환불금액비율", "결제상품수량", "결제당 상품수량", "환불상품수량", "환불상품비율", "방문수",
    "구매전환율", "배송비", "전체 할인액", "판매자 부담 상품할인액", "네이버 부담 상품할인액", "판매자 부담 주문할인액",
    "네이버 부담 주문할인액",
]

CHANNELS = [  # (1단계, 2단계, 3단계, 8월 방문 비중, 8월 전환율%)
    ("검색", "네이버쇼핑", "검색", 0.34, 5.2),
    ("검색", "네이버", "통합검색", 0.18, 4.4),
    ("검색", "구글", "검색", 0.05, 3.0),
    ("광고", "네이버", "쇼핑검색광고", 0.12, 4.9),
    ("광고", "네이버", "성과형디스플레이", 0.06, 1.8),
    ("SNS", "인스타그램", "-", 0.07, 2.1),
    ("SNS", "블로그", "-", 0.05, 3.3),
    ("직접유입", "-", "-", 0.08, 6.8),
    ("기타", "-", "-", 0.05, 2.5),
]

KEYWORDS = [  # (검색어, 8월 방문수, 8월 전환율%)
    ("무선 이어폰", 3200, 4.6), ("보조배터리", 2100, 5.4), ("블루투스 스피커", 1500, 3.2), ("고속 충전기", 1900, 6.1),
    ("스마트워치 스트랩", 900, 4.9), ("노트북 파우치", 700, 3.8), ("무선 마우스", 1400, 4.7), ("기계식 키보드", 1100, 2.4),
    ("usb 허브", 600, 3.5), ("휴대폰 거치대", 1300, 7.0), ("가성비 이어폰", 800, 3.9), ("대용량 보조배터리", 650, 5.8),
    ("캠핑 스피커", 420, 2.9), ("아이폰 충전기", 980, 6.6), ("저소음 마우스", 510, 5.1), ("적축 키보드", 330, 2.0),
    ("차량용 거치대", 740, 6.2), ("노트북 가방", 450, 2.7), ("c타입 허브", 380, 3.9), ("갤럭시워치 스트랩", 290, 5.5),
]


def _pct(a: float, b: float) -> float:
    return round(a / b * 100, 2) if b else 0


def _sales(month: str, rng: random.Random) -> pd.DataFrame:
    sep = month == "2026-09"
    rows = []
    for pid, name, price, visits, cvr in PRODUCTS:
        v = int(visits * (1.18 if sep else 1.0) * rng.uniform(0.95, 1.05))
        c = cvr * (0.85 if sep else 1.0) * rng.uniform(0.95, 1.05)
        orders = max(1, round(v * c / 100))
        qty = round(orders * rng.uniform(1.0, 1.3))
        gross = qty * price
        refund_ratio = (0.20 if sep else 0.03) if pid == "P1003" else rng.uniform(0.01, 0.05)
        refunds = round(orders * refund_ratio)
        refund_qty = round(qty * refund_ratio)
        refund_amount = refund_qty * price
        discount = round(gross * (0.09 if sep else 0.05) * rng.uniform(0.9, 1.1))
        seller_prod = round(discount * 0.55)
        naver_prod = round(discount * 0.15)
        seller_order = round(discount * 0.25)
        naver_order = discount - seller_prod - naver_prod - seller_order
        rows.append([
            "결제일", MONTHS[month][2], name, pid, orders, refunds, _pct(refunds, orders), gross, gross - refund_amount,
            round(gross / orders), refund_amount, _pct(refund_amount, gross), qty, round(qty / orders, 2), refund_qty,
            _pct(refund_qty, qty), v, _pct(orders, v), orders * 3000, discount, seller_prod, naver_prod, seller_order, naver_order,
        ])
    return pd.DataFrame(rows, columns=SALES_COLUMNS)


def _visit(month: str, rng: random.Random, total_visits: int, aov: int) -> pd.DataFrame:
    sep = month == "2026-09"
    rows = []
    for l1, l2, l3, share, cvr in CHANNELS:
        shopping_search = (l2, l3) == ("네이버쇼핑", "검색")
        v = int(total_visits * share * (1.3 if sep and shopping_search else 1.0) * rng.uniform(0.95, 1.05))
        c = cvr * (0.7 if sep and shopping_search else 1.0) * rng.uniform(0.95, 1.05)
        orders = round(v * c / 100)
        revenue = orders * aov
        rows.append([MONTHS[month][2], l1, l2, l3, v, orders, _pct(orders, v), revenue, round(revenue / orders) if orders else 0])
    return pd.DataFrame(rows, columns=["날짜", "경로(1단계)", "경로(2단계)", "경로(3단계)", "방문수", "상품결제건수", "구매전환율", "판매금액(총)", "상품결제단가"])


def _query(month: str, rng: random.Random, aov: int) -> pd.DataFrame:
    sep = month == "2026-09"
    rows = []
    for kw, visits, cvr in KEYWORDS:
        hot = kw == "무선 이어폰"
        v = int(visits * ((1.6 if hot else 1.1) if sep else 1.0) * rng.uniform(0.93, 1.07))
        c = cvr * ((0.55 if hot else 0.95) if sep else 1.0) * rng.uniform(0.93, 1.07)
        orders = round(v * c / 100)
        revenue = orders * aov
        rows.append([MONTHS[month][2], kw, v, orders, _pct(orders, v), revenue, round(revenue / orders) if orders else 0])
    return pd.DataFrame(rows, columns=["날짜", "검색어", "방문수", "상품결제건수", "구매전환율", "판매금액(총)", "상품결제단가"])


def _customer(month: str, rng: random.Random, total_visits: int, aov: int) -> pd.DataFrame:
    sep = month == "2026-09"
    groups = {"신규": (0.72 if sep else 0.65, 2.6), "재구매": (0.28 if sep else 0.35, 7.5 if sep else 8.4)}
    per = {}
    for g, (share, cvr) in groups.items():
        visitors = int(total_visits * 0.8 * share)
        buyers = round(visitors * cvr / 100 * rng.uniform(0.95, 1.05))
        per[g] = (visitors, buyers, buyers * round(aov * (1.25 if g == "재구매" else 1.0)))
    tv, tb, tr = (sum(x[i] for x in per.values()) for i in range(3))
    date = MONTHS[month][2]
    rows = [[date, "전체합산", tv, "-", tb, "-", _pct(tb, tv), tr, "-", round(tr / tb)]]
    for g, (v, b, r) in per.items():
        rows.append([date, g, v, _pct(v, tv), b, _pct(b, tb), _pct(b, v), r, _pct(r, tr), round(r / b) if b else 0])
    return pd.DataFrame(rows, columns=["날짜", "고객분류", "방문고객수", "방문고객수비중", "결제고객수", "결제고객수비중", "구매전환율(고객)", "판매금액(총)", "판매금액(총)비중", "객단가"])


def main() -> None:
    for month, (start, end, _) in MONTHS.items():
        rng = random.Random(f"smartstore-{month}")
        sales = _sales(month, rng)
        total_visits = int(sales["방문수"].sum())
        aov = round(sales["판매금액(총)"].sum() / sales["상품결제건수"].sum())
        frames = {
            "sales": ("SALES", sales),
            "visit": ("VISIT", _visit(month, rng, total_visits, aov)),
            "query": ("QUERY", _query(month, rng, aov)),
            "customer": ("CUSTOMER", _customer(month, rng, total_visits, aov)),
        }
        for kind, (sheet, df) in frames.items():
            path = OUT / f"{kind}_{start}-{end}_sample.xlsx"
            df.to_excel(path, sheet_name=sheet, index=False)
            print(path.name, df.shape)


if __name__ == "__main__":
    main()
