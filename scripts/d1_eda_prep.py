"""1일차: 탐색 분석(EDA)용 바이어 표를 메모리에서 만든다 (원본 · 코드표는 읽기만).

쓰는 곳: workbench/day1/notebooks/d1_eda.ipynb 첫 셀 (`from d1_eda_prep import load_analysis_table`)
단독 실행: uv run python scripts/d1_eda_prep.py  → 정리 결과 요약만 출력, 파일은 쓰지 않는다.
근거: workbench/day1/outputs/d1_quality_report.md (진단) · d1_code_table.csv (결제방식 코드표)

정리 규칙
  1. 중복: buyer_id 기준 첫 행만 남김 (B047 · B094 · B114, 153 → 150행)
  2. max_dpd_days: 숫자 셀 그대로, '90일' · '381 days'처럼 단위만 붙은 글자는 숫자만 추출.
     '-' · '확인중'처럼 값이 아닌 글자는 결측(NaN) — 0으로 바꾸지 않는다.
  3. payment_method: d1_code_table.csv(사람이 확인한 코드표)를 공백 제거 · 대문자 키로 매핑.
     '검토 필요'는 그대로 둔다. 코드표에 없는 표기는 '미분류'.
  4. country_name: country_code별 가장 많이 쓴 표기로 다시 붙임 (오타 · 약어 · 한글 표기 정리)
  5. ar_balance · overdue_amount: 숫자 셀 그대로, 천단위 쉼표 · 'USD ' 접두만 숫자로 변환.
     'k' · '약 …' 어림값은 결측 (원장 대조 전 확인 필요).
  6. ar_currency: usd · US$ → USD, € → EUR. '¥'는 JPY/CNY 겹침이라 그대로 둔다 (확인 필요).
  7. is_overdue = max_dpd_days > 0 (연체일이 결측이면 판정 불가 → NA)
"""
import re
import sys

import pandas as pd

SRC = "data/day1/d1_buyers_raw.xlsx"
CODE_TABLE = "workbench/day1/outputs/d1_code_table.csv"
UNMAPPED = "미분류"
CURRENCY_MAP = {"usd": "USD", "US$": "USD", "€": "EUR"}


def norm_key(v):
    # 코드표 매핑용 키: 앞뒤 공백 제거 · 연속 공백 하나로 · 대문자
    return re.sub(r"\s+", " ", str(v).strip().upper())


def parse_dpd(v):
    if isinstance(v, (int, float)):
        return float(v)
    m = re.fullmatch(r"\s*(\d+)\s*(일|days?)\s*", str(v), flags=re.I)
    return float(m.group(1)) if m else float("nan")


def parse_amount(v):
    if isinstance(v, (int, float)):
        return float(v)
    s = re.sub(r"^\s*USD\s*", "", str(v)).replace(",", "").strip()
    return float(s) if re.fullmatch(r"\d+(\.\d+)?", s) else float("nan")


def load_code_map(path=CODE_TABLE):
    ct = pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    ct["key"] = ct["원래 표기"].map(norm_key)
    conflict = ct.groupby("key")["표준 코드"].nunique()
    assert (conflict == 1).all(), f"같은 키에 코드가 둘 이상: {conflict[conflict > 1].index.tolist()}"
    return dict(zip(ct["key"], ct["표준 코드"]))


def load_analysis_table(src=SRC, code_table=CODE_TABLE):
    raw = pd.read_excel(src, sheet_name="buyers", dtype=object)
    raw.insert(0, "excel_row", raw.index + 2)  # 1행은 머리글

    # 1) 중복 제거
    df = raw.drop_duplicates("buyer_id", keep="first").reset_index(drop=True)

    # 2) 연체일
    df["max_dpd_days_raw"] = df["max_dpd_days"]
    df["max_dpd_days"] = df["max_dpd_days_raw"].map(parse_dpd)

    # 3) 결제방식 표준 코드
    code_map = load_code_map(code_table)
    df["payment_method"] = df["payment_terms_raw"].map(lambda v: code_map.get(norm_key(v), UNMAPPED))

    # 4) 국가명
    name_by_code = raw.groupby("country_code")["country"].agg(lambda s: s.value_counts().index[0])
    df["country_name"] = df["country_code"].map(name_by_code)

    # 5) 금액 · 6) 통화
    for c in ["ar_balance", "overdue_amount"]:
        df[c + "_raw"] = df[c]
        df[c] = df[c + "_raw"].map(lambda v: parse_amount(v) if pd.notna(v) else float("nan"))
    df["ar_currency"] = df["ar_currency"].replace(CURRENCY_MAP)

    # 7) 연체 여부 (판정 불가 = NA)
    df["is_overdue"] = (df["max_dpd_days"] > 0).astype("boolean")
    df.loc[df["max_dpd_days"].isna(), "is_overdue"] = pd.NA

    log = {
        "원본 행": len(raw),
        "중복 제거 후 행": len(df),
        "제거된 중복 buyer_id": sorted(raw.loc[raw.duplicated("buyer_id"), "buyer_id"]),
        "연체일 판정 불가": df.loc[df["max_dpd_days"].isna(), ["buyer_id", "max_dpd_days_raw"]].values.tolist(),
        "연체일 단위 제거": df.loc[df["max_dpd_days_raw"].map(lambda v: isinstance(v, str)) & df["max_dpd_days"].notna(),
                             ["buyer_id", "max_dpd_days_raw"]].values.tolist(),
        "결제방식 검토 필요·미분류": df.loc[df["payment_method"].isin(["검토 필요", UNMAPPED]),
                                   ["buyer_id", "payment_terms_raw", "payment_method"]].values.tolist(),
    }
    return df, log


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    df, log = load_analysis_table()
    for k, v in log.items():
        print(f"{k}: {v}")
    print(df["payment_method"].value_counts().to_string())
