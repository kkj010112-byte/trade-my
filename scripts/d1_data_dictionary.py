"""1일차: d1_buyers_raw 데이터 사전용 관측값(결측 수 · 실제 범위 · 값 종류) 계산 (원본은 읽기만).

실행: uv run python scripts/d1_data_dictionary.py
쓰임: workbench/day1/outputs/d1_data_dictionary.md 의 '결측 수' · '관측' 숫자 근거.
뜻 · 단위 · 공식은 data/data_dictionary.xlsx columns · codes 시트에서 가져온다.
"""
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
SRC = "data/day1/d1_buyers_raw.xlsx"
DICT = "data/data_dictionary.xlsx"

df = pd.read_excel(SRC, sheet_name="buyers", dtype=object)
cols = pd.read_excel(DICT, sheet_name="columns", dtype=object)
cols = cols[cols.file == "d1_buyers_raw"].set_index("column")

print(f"행 {len(df)} · 열 {df.shape[1]} · 사전에 없는 열: {sorted(set(df.columns) - set(cols.index))}")
for c in df.columns:
    s = df[c]
    kinds = s.dropna().map(lambda v: type(v).__name__).value_counts().to_dict()
    line = f"\n[{c}] 사전 dtype={cols.dtype.get(c)} · 결측 {s.isna().sum()} · 셀 유형 {kinds} · 종류 {s.nunique()}"
    num = pd.to_numeric(s, errors="coerce")
    if cols.dtype.get(c) in ("number", "integer", "number/text"):
        line += f" · 숫자로 읽힘 {num.notna().sum()} · 최소 {num.min()} · 최대 {num.max()}"
        if c == "debt_to_equity_fy2025":
            line += f" · 음수 {(num < 0).sum()}"
    elif s.nunique() <= 25:
        line += f" · 값 {s.value_counts().to_dict()}"
    print(line)
