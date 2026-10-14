"""1일차: payment_terms_raw 표기 → 표준 결제방식 코드 7종 매핑표 (원본은 읽기만).

실행: uv run python scripts/d1_code_table.py
결과: workbench/day1/outputs/d1_code_table.csv (utf-8-sig, 엑셀에서 한글 유지)
근거: data/data_dictionary.xlsx codes 시트(payment_method 정의). 애매하면 '검토 필요'.
마지막에 payment_terms_map(과정 기본 코드표)과 대조만 하고, 결과에는 섞지 않는다.
"""
import re
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
SRC = "data/day1/d1_buyers_raw.xlsx"
DICT = "data/data_dictionary.xlsx"
OUT = "workbench/day1/outputs/d1_code_table.csv"
REVIEW = "검토 필요"

raw = pd.read_excel(SRC, sheet_name="buyers", dtype=object).payment_terms_raw
variants = sorted(raw.dropna().unique(), key=lambda v: v.strip().upper())


def norm(v):
    # 앞뒤 공백 제거 · 대문자 · 연속 공백 하나로 (판정용 키, 원래 표기는 그대로 남김)
    return re.sub(r"\s+", " ", v.strip().upper())


def hit(pattern, v):
    m = re.search(pattern, norm(v))
    return m.group(0) if m else None


def classify(v):
    """(코드, 판단 근거, 확신). 규칙은 위에서부터 먼저 맞는 것 하나만 쓴다."""
    k = norm(v)
    # 1) 분할 송금: 30/70 비율이 보일 때만 TT_SPLIT_30_70
    if w := hit(r"30\s*[/:]\s*70|30% T/T ADVANCE, 70%", v):
        return "TT_SPLIT_30_70", f"'{w}' — 선수 30% + 잔금 70%", "높음"
    # 2) 선수금 (100% 선수도 여기)
    if w := hit(r"IN ADVANCE|BEFORE SHIPMENT", v):
        return "TT_ADV", f"'{w}' — 선적 전 송금", "높음"
    if "%" in k:
        return REVIEW, "선수 비율이 30/70이 아님(10%+90%) · O/A가 섞여 코드 7개 중 어디에도 맞지 않음", "낮음"
    # 3) 신용장
    if hit(r"\bL/?C\b|신용장", v):
        if w := hit(r"SIGHT|일람불", v):
            return "LC_SIGHT", f"L/C + '{w}' — 일람불", "높음"
        if w := hit(r"USANCE", v):
            return "LC_USANCE", f"L/C + '{w}' — 기한부", "높음"
        if w := hit(r"\d+ DAYS", v):
            return "LC_USANCE", f"L/C + '{w}' — 일수만 있음(USANCE 단어 없음). 신용장 유효기간일 수도 있음", "낮음"
        return REVIEW, "L/C만 있고 일람불/기한부 구분 단어 없음", "낮음"
    # 4) 추심
    if w := hit(r"\bD/?P(?=\d|\b)|DOCUMENTS AGAINST PAYMENT", v):
        return "DP", f"'{w}' — Documents against payment", "높음"
    if w := hit(r"\bD/?A(?=\d|\b)|DOCUMENTS AGAINST ACCEPTANCE", v):
        return "DA", f"'{w}' — Documents against acceptance", "높음"
    # 5) 사후송금
    if w := hit(r"\bO/?A(?=\d|\b)|OPEN ACC(OUN)?T", v):
        return "OA", f"'{w}' — Open account", "높음"
    if w := hit(r"\bNET \d+", v):
        return "OA", f"'{w}' — Net N(codes 시트: OA에 Net N 포함)", "높음"
    if w := hit(r"\bT/?T\b.*?\d+ ?DAYS", v):
        return "OA", f"'{w}' — T/T + 일수 = 사후송금(codes 시트 OA 설명)", "높음"
    # 6) T/T만 있고 시점이 없음
    if hit(r"^T/?T$", v):
        return REVIEW, "T/T(송금)만 있고 선적 전/후 시점이 없음 — 선수금인지 사후송금인지 알 수 없음", "낮음"
    return REVIEW, "규칙에 맞는 단어 없음", "낮음"


rows = [(v, *classify(v)) for v in variants]
tbl = pd.DataFrame(rows, columns=["원래 표기", "표준 코드", "판단 근거(어느 단어로)", "확신(높음/낮음)"])
tbl.to_csv(OUT, index=False, encoding="utf-8-sig")

counts = raw.value_counts()
tbl["행 수"] = tbl["원래 표기"].map(counts)
print(f"표기 {len(tbl)}종 / {int(tbl['행 수'].sum())}행 → {OUT}")
print(tbl.groupby("표준 코드").agg(표기=("원래 표기", "size"), 행=("행 수", "sum")).to_string())
print(tbl.groupby("확신(높음/낮음)")["행 수"].agg(["size", "sum"]).to_string())
print("\n[검토 필요 · 확신 낮음]")
print(tbl[tbl["확신(높음/낮음)"] == "낮음"].to_string(index=False))

# 과정 기본 코드표와 대조 (raw_upper = TRIM · UPPER 키)
ref = pd.read_excel(DICT, sheet_name="payment_terms_map", header=2)
ref_map = dict(zip(ref.raw_upper, ref.payment_method))
tbl["기본표"] = tbl["원래 표기"].map(lambda v: ref_map.get(v.strip().upper()))
print("\n[기본 코드표 대조]")
print("기본표에 없는 표기:", tbl[tbl["기본표"].isna()]["원래 표기"].map(repr).tolist())
diff = tbl[tbl["기본표"].notna() & (tbl["기본표"] != tbl["표준 코드"])]
print("코드가 다른 표기:")
print(diff[["원래 표기", "표준 코드", "기본표", "행 수"]].to_string(index=False))
