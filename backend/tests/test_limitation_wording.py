from app.ai.facts import EvidenceCatalogue


def test_supported_exports_and_id_boundary_are_described():
    wording = " ".join(EvidenceCatalogue().limitations)
    assert "쿠팡 판매·광고 리포트" in wording
    assert "네이버 쇼핑검색광고 소재 보고서" in wording
    assert "상품 ID가 다른 판매·광고 자료는 상품 단위로 연결하지 않습니다" in wording
    assert "실제 판매·광고 원본 리포트의 자동 분리·병합은 지원하지 않습니다" not in wording
