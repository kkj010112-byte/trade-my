"""1일차: d1_buyers_raw.xlsx 품질 진단 (읽기 전용 · 고치지 않는다).

실행: uv run python scripts/d1_quality_check.py
결과 숫자는 workbench/day1/outputs/d1_quality_report.md 에 옮겨 적는다.
"""
import re
import sys

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
SRC = "data/day1/d1_buyers_raw.xlsx"
ASOF = pd.Timestamp("2026-09-30")

# dtype=object 로 읽어 엑셀 셀의 원래 형식(숫자 셀 / 글자 셀)을 그대로 본다
df = pd.read_excel(SRC, sheet_name="buyers", dtype=object)
df.insert(0, "excel_row", df.index + 2)  # 1행은 머리글
print("shape", df.shape)


def section(t):
    print(f"\n=== {t} ===")


# 1) 열별 유형 · 결측
section("열별 셀 유형 · 결측")
for c in df.columns[1:]:
    s = df[c]
    types = s.dropna().map(lambda v: type(v).__name__).value_counts().to_dict()
    print(f"{c}: null={s.isna().sum()} types={types} nunique={s.nunique()}")

# 앞뒤 공백 · 이중 공백
section("앞뒤/이중 공백")
for c in df.columns[1:]:
    s = df[c].dropna()
    s = s[s.map(lambda v: isinstance(v, str))]
    bad = s[(s != s.str.strip()) | s.str.contains("  ")]
    if len(bad):
        print(c, bad.map(repr).tolist()[:5], len(bad))

# 2) 중복
section("중복")
key = df.columns[1:]
print("완전 중복 행:", df[df.duplicated(subset=key, keep=False)][["excel_row", "buyer_id"]].values.tolist())
dup_id = df[df.duplicated("buyer_id", keep=False)].sort_values("buyer_id")
for bid, g in dup_id.groupby("buyer_id"):
    diff = [c for c in key if g[c].astype(str).nunique() > 1]
    print(bid, "rows", g.excel_row.tolist(), "다른 열:", diff, {c: g[c].tolist() for c in diff})
norm_name = df.buyer_name.str.lower().str.replace(r"[^a-z0-9]", "", regex=True)
dn = df[norm_name.duplicated(keep=False)]
print("이름 중복(정규화):", dn[["excel_row", "buyer_id", "buyer_name"]].values.tolist())

# 3) 국가
section("country ↔ country_code")
print(df.groupby("country_code").country.unique().to_dict())
print(df.groupby("country_code").region.unique().to_dict())

# 4) 업종 · 구분
section("industry · segment · buyer_type")
print(df[df.industry.isna()][["excel_row", "buyer_id", "segment", "buyer_type"]].values.tolist())
print(pd.crosstab(df.industry.fillna("(빈칸)"), df.segment))
print(pd.crosstab(df.segment, df.buyer_type))

# 5) 결제조건
section("payment_terms_raw 표기")
print(df.payment_terms_raw.value_counts().to_string())

# 6) 숫자처럼 보이는 글자 · 숫자 열의 글자 셀
section("숫자 열의 글자 셀")
num_cols = ["ar_balance", "max_dpd_days", "overdue_amount", "pay_score", "oecd_crc",
            "revenue_usd_fy2025", "current_ratio_fy2025", "debt_to_equity_fy2025",
            "dso_fy2025", "op_margin_fy2025"]
for c in num_cols:
    s = df[[c, "excel_row", "buyer_id"]].dropna()
    t = s[s[c].map(lambda v: isinstance(v, str))]
    for _, r in t.iterrows():
        print(c, r.excel_row, r.buyer_id, repr(r[c]))
# 정수 열에 실수 / 실수 열에 정수
print("dso int:", df[df.dso_fy2025.map(lambda v: isinstance(v, int))][["excel_row", "buyer_id", "dso_fy2025"]].values.tolist())
print("overdue float:", df[df.overdue_amount.map(lambda v: isinstance(v, float) and v == v)][["excel_row", "buyer_id", "overdue_amount"]].values.tolist())
print("ar_balance float:", df[df.ar_balance.map(lambda v: isinstance(v, float))][["excel_row", "buyer_id", "ar_balance"]].values.tolist())

# 7) 통화
section("ar_currency")
print(df.ar_currency.value_counts().to_string())
print(df[df.ar_currency.isin(["¥", "€", "US$", "usd"])][["excel_row", "buyer_id", "country_code", "ar_currency"]].values.tolist())
print(pd.crosstab(df.country_code, df.ar_currency).to_string())

# 8) 날짜 형식
section("since_date 형식")
pats = [
    ("YYYY-MM-DD", r"^\d{4}-\d{2}-\d{2}$"),
    ("YYYY.M.D", r"^\d{4}\.\d{1,2}\.\d{1,2}$"),
    ("DD/MM/YYYY 또는 MM/DD/YYYY", r"^\d{2}/\d{2}/\d{4}$"),
    ("Mon D YYYY", r"^[A-Z][a-z]{2} \d{1,2} \d{4}$"),
]


def fmt(v):
    for n, p in pats:
        if re.match(p, str(v)):
            return n
    return "기타"


df["_fmt"] = df.since_date.map(fmt)
for n, g in df.groupby("_fmt"):
    print(n, len(g), g.since_date.head(3).tolist())
sl = df[df._fmt.str.startswith("DD/")].since_date.str.split("/", expand=True).astype(int)
print("슬래시: 첫칸>12", (sl[0] > 12).sum(), "둘째칸>12", (sl[1] > 12).sum(),
      "둘다<=12(모호)", ((sl[0] <= 12) & (sl[1] <= 12)).sum())
amb = df[df._fmt.str.startswith("DD/")][((sl[0] <= 12) & (sl[1] <= 12)).values]
print("모호 예:", amb[["excel_row", "buyer_id", "since_date"]].values.tolist())


def parse(v):
    f = fmt(v)
    if f == "YYYY-MM-DD":
        return pd.to_datetime(v, format="%Y-%m-%d")
    if f == "YYYY.M.D":
        return pd.to_datetime(v, format="%Y.%m.%d")
    if f.startswith("DD/"):
        return pd.to_datetime(v, format="%d/%m/%Y", errors="coerce")
    if f == "Mon D YYYY":
        return pd.to_datetime(v, format="%b %d %Y")
    return pd.NaT


d = df.since_date.map(parse)
print("기준일 이후:", df[d > ASOF][["excel_row", "buyer_id", "since_date"]].values.tolist())
print("범위:", d.min(), d.max())

# 9) 논리 점검
section("논리 점검")
num = lambda c: pd.to_numeric(df[c], errors="coerce")
ar, od, dpd = num("ar_balance"), num("overdue_amount"), num("max_dpd_days")
print("dpd>0 & overdue=0:", df[(dpd > 0) & (od == 0)][["excel_row", "buyer_id", "max_dpd_days", "overdue_amount"]].values.tolist())
print("dpd=0 & overdue>0:", df[(dpd == 0) & (od > 0)][["excel_row", "buyer_id", "max_dpd_days", "overdue_amount"]].values.tolist())
print("overdue>ar:", df[od > ar][["excel_row", "buyer_id", "ar_balance", "overdue_amount"]].values.tolist())
print("ar 결측:", df[df.ar_balance.isna()][["excel_row", "buyer_id", "max_dpd_days", "overdue_amount"]].values.tolist())
ps = num("pay_score")
print("pay_score 범위", ps.min(), ps.max(), "60 미만:", df[ps < 60][["excel_row", "buyer_id", "pay_score"]].values.tolist())
print("dpd 분포(>0):", sorted(dpd[dpd > 0].tolist()))
print("oecd '-' 국가:", sorted(df[df.oecd_crc == "-"].country_code.unique()))
print("oecd 숫자 국가:", df[df.oecd_crc != "-"].groupby("country_code").oecd_crc.unique().to_dict())

# 10) 재무
section("재무")
for c in ["revenue_usd_fy2025", "current_ratio_fy2025", "debt_to_equity_fy2025", "dso_fy2025", "op_margin_fy2025"]:
    print(c, num(c).describe().round(4).to_dict())
nr = df.fin_summary_text.str.contains("not received")
print("미수령 문구", nr.sum(), "그중 매출 빈칸", df[nr].revenue_usd_fy2025.isna().sum())
print("매출 빈칸인데 미수령 문구 아님:", df[df.revenue_usd_fy2025.isna() & ~nr][["excel_row", "buyer_id", "fin_summary_text"]].values.tolist())
print("일부 미공개 문구:", df.fin_summary_text.str.contains("not disclosed").sum())
# 요약문의 매출 · 영업이익률과 숫자 열 대조
m = df.fin_summary_text.str.extract(r"USD ([\d.]+)M")[0].astype(float)
rev_m = num("revenue_usd_fy2025") / 1e6
mis = df[(m.notna()) & (rev_m.notna()) & ((m - rev_m).abs() > 0.051)]
print("요약문 매출 불일치:", mis[["excel_row", "buyer_id", "revenue_usd_fy2025", "fin_summary_text"]].values.tolist())
mm = df.fin_summary_text.str.extract(r"(-?[\d.]+)% margin|operating margin (-?[\d.]+)%")
pm = pd.to_numeric(mm[0].fillna(mm[1]), errors="coerce") / 100
opm = num("op_margin_fy2025")
mis = df[pm.notna() & opm.notna() & ((pm - opm).abs() > 0.0006)]
print("요약문 이익률 불일치:", mis[["excel_row", "buyer_id", "op_margin_fy2025", "fin_summary_text"]].values.tolist())
de = num("debt_to_equity_fy2025")
print("D/E 음수:", df[de < 0][["excel_row", "buyer_id", "debt_to_equity_fy2025"]].values.tolist())
print("현재 이익률 |x|>1:", df[opm.abs() > 1][["excel_row", "buyer_id", "op_margin_fy2025"]].values.tolist())
