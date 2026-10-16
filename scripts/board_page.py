"""3일차 실습 D: 바이어 리스크 보드(v2 · B 다크 금융 터미널)를 만든다.

입력: labs/day3/lab-d/buyer_board.csv (읽기만)
토큰: workbench/day3/outputs/design.md 2절 → 아래 TOKENS
출력: workbench/day3/outputs/buyer_board.html (파일 하나, 같은 입력이면 같은 결과)
실행: uv run python scripts/board_page.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

# design.md 2절의 토큰. 화면의 색 · 글자 크기 · 간격 · 모서리는 이 값만 쓴다.
TOKENS = {
    # 색 6개
    "color-bg": "#0D131E",  # v2에서 바뀜
    "color-surface": "#141C2A",  # v2에서 바뀜
    "color-border": "#2A3546",  # v2에서 바뀜
    "color-text": "#E7EBF1",  # v2에서 바뀜
    "color-text-muted": "#9BA6B5",  # v2에서 바뀜
    "color-accent": "#8CC0E8",  # v2에서 바뀜
    # 등급 색 4개 + 등급 면 위 글자
    "grade-s": "#5CC08A",  # v2에서 바뀜
    "grade-a": "#B9C653",  # v2에서 바뀜
    "grade-b": "#E9A452",  # v2에서 바뀜
    "grade-c": "#F2766B",  # v2에서 바뀜
    "grade-on": "#0D131E",  # v2에서 바뀜
    # 글꼴
    "font-sans": "'IBM Plex Sans KR', sans-serif",  # v2에서 바뀜
    # 글자 크기 6단계
    "fs-xs": "12px",
    "fs-sm": "13px",  # v2에서 바뀜
    "fs-md": "14px",  # v2에서 바뀜
    "fs-lg": "16px",  # v2에서 바뀜
    "fs-xl": "24px",  # v2에서 바뀜
    "fs-2xl": "32px",  # v2에서 바뀜
    # 간격(4의 배수)
    "sp-1": "4px",
    "sp-2": "8px",
    "sp-3": "12px",
    "sp-4": "16px",
    "sp-6": "24px",
    "sp-8": "32px",
    "sp-12": "48px",
    # 모서리 · 그림자
    "radius-sm": "2px",  # v2에서 바뀜
    "radius-md": "4px",  # v2에서 바뀜
    "shadow": "none",
    # 레이아웃 값(design.md 2-7)
    "layout-max": "1280px",
    "label-col": "128px",
    "focus-ring": "2px",
    # 지역 타일 · 히트맵(design.md 2-8, v3에서 더함)
    "heat-c-1": "#1A2230",
    "heat-c-2": "#4A2427",
    "heat-c-3": "#A23C35",
    "heat-c-4": "#F2766B",
    "heat-c-on-1": "#E7EBF1",
    "heat-c-on-2": "#E7EBF1",
    "heat-c-on-3": "#E7EBF1",
    "heat-c-on-4": "#0D131E",
    "grade-s-soft": "#183427",
    "grade-a-soft": "#2E3418",
    "grade-b-soft": "#3A2914",
    "grade-c-soft": "#3F201D",
    # 경영진 한 장(design.md 2-9, v3에서 더함): 흑백 인쇄용
    "print-bg": "#FFFFFF",
    "print-text": "#111111",
    "print-muted": "#444444",
    "print-line": "#8A8A8A",
    "sheet-w": "794px",
}

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "labs/day3/lab-d/buyer_board.csv"
OUT = ROOT / "workbench/day3/outputs/buyer_board.html"

REF_DATE = "2026-09-30"
DEFAULT_LINE = 17  # 위험 선(%)

COUNTRY_KO = {
    "ARE": "아랍에미리트", "BRA": "브라질", "CHN": "중국", "DEU": "독일",
    "EGY": "이집트", "GBR": "영국", "IDN": "인도네시아", "IND": "인도",
    "JPN": "일본", "MEX": "멕시코", "MYS": "말레이시아", "NGA": "나이지리아",
    "NLD": "네덜란드", "POL": "폴란드", "SAU": "사우디아라비아", "THA": "태국",
    "TUR": "튀르키예", "TWN": "대만", "USA": "미국", "VNM": "베트남",
}


def grade_of(pd_bp: int, line: int) -> str:
    """등급 규칙(C부터 검사). 정수 비교: pd_bp = pd_30d × 10000, line = %."""
    if pd_bp >= 100 * line:
        return "C"
    if 2 * pd_bp >= 100 * line:
        return "B"
    if 4 * pd_bp >= 100 * line:
        return "A"
    return "S"


# 지역 타일 배치(7절 ③). 대략의 지리 배치를 CSS 격자 이름으로.
REGION_AREA = {
    "북미·중남미": "na", "서유럽": "we", "중동부유럽": "ce",
    "중동·아프리카": "me", "동아시아": "ea", "동남아·남아": "sa",
}


def load() -> pd.DataFrame:
    df = pd.read_csv(SRC, encoding="utf-8-sig")
    if set(df["region"]) != set(REGION_AREA):
        sys.exit(f"REGION_AREA와 다른 지역: {sorted(set(df['region']) ^ set(REGION_AREA))}")
    unknown = sorted(set(df["country_code"]) - set(COUNTRY_KO))
    if unknown:
        sys.exit(f"COUNTRY_KO에 없는 나라 코드: {unknown}")
    df["country_ko"] = df["country_code"].map(COUNTRY_KO)
    df["pd_bp"] = (df["pd_30d"] * 10000).round().astype(int)
    if not ((df["pd_bp"] / 10000 - df["pd_30d"]).abs() < 1e-9).all():
        sys.exit("pd_30d에 소수 넷째 자리보다 긴 값이 있어 정수 비교를 쓸 수 없습니다.")
    return df.sort_values("buyer_id").reset_index(drop=True)


def report(df: pd.DataFrame) -> None:
    regraded = df["pd_bp"].apply(lambda b: grade_of(b, DEFAULT_LINE))
    match = int((regraded == df["grade"]).sum())
    print(f"grade 열 vs {DEFAULT_LINE}% 규칙: {match}/{len(df)} 일치")
    if match != len(df):
        print("  경고: 다른 줄", df.loc[regraded != df["grade"], "buyer_id"].tolist())

    total_ar = int(df["open_ar_usd"].sum())
    print("\n| 등급 | 곳 수 | 채권 |\n|---|---:|---:|")
    for g in "SABC":
        sub = df[df["grade"] == g]
        print(f"| {g} | {len(sub)} | ${int(sub['open_ar_usd'].sum()):,} |")
    c_ar = int(df.loc[df["grade"] == "C", "open_ar_usd"].sum())
    print(f"\nC등급 채권 ${c_ar:,} / 전체 채권 ${total_ar:,} ({c_ar / total_ar * 100:.1f}%)")
    od = df[df["overdue_usd"] > 0]
    print(f"연체 금액 ${int(od['overdue_usd'].sum()):,} · {len(od)}곳")

    reg = df.groupby("region")["open_ar_usd"].sum()
    c_reg = df[df["grade"] == "C"].groupby("region")["open_ar_usd"].sum().reindex(reg.index, fill_value=0)
    grid = pd.crosstab(df["region"], df["grade"])
    print(f"\n지역별 채권 합 ${int(reg.sum()):,} = 전체 채권 ${total_ar:,}: {int(reg.sum()) == total_ar}")
    print(f"지금 선({DEFAULT_LINE}%)에서 C등급 채권이 가장 많은 지역: {c_reg.idxmax()} ${int(c_reg.max()):,}")
    print(f"격자 칸 곳 수의 합: {int(grid.values.sum())}")
    print("| 지역 | 채권 | 곳 수 | C등급 채권 | C 비중 |\n|---|---:|---:|---:|---:|")
    for k in reg.sort_values(ascending=False).index:
        print(f"| {k} | ${int(reg[k]):,} | {int((df['region'] == k).sum())} | ${int(c_reg[k]):,} | {c_reg[k] / reg[k] * 100:.1f}% |")

    base_n = (df["pd_bp"] >= 100 * DEFAULT_LINE).sum()
    print("\n슬라이더 대조값(C등급 곳 수 · 채권 · 17%와 차이)")
    for line in (16, 10, 5, 20, 30):
        m = df["pd_bp"] >= 100 * line
        ar = int(df.loc[m, "open_ar_usd"].sum())
        print(f"  {line}%: {m.sum()}곳 · ${ar:,} · {m.sum() - base_n:+d}곳 · {ar - c_ar:+,}")


def top10_detail(df: pd.DataFrame) -> dict:
    """상세 패널(7절 ①)용: 위험 상위 10곳만, 패널에 보일 열만. 빈칸은 None(→ JSON null)."""
    top = df.sort_values(["pd_bp", "buyer_id"], ascending=[False, True]).head(10)
    out = {}
    for r in top.itertuples():
        pm = None if pd.isna(r.pct_ar_31p) else int(round(r.pct_ar_31p * 1000))  # 비율 × 1000(정수)
        if pm is not None and abs(pm / 1000 - r.pct_ar_31p) > 1e-9:
            sys.exit(f"{r.buyer_id}: pct_ar_31p가 소수 셋째 자리보다 깁니다.")
        out[r.buyer_id] = {
            "industry": r.industry,
            "payment": r.payment_method,
            "terms": int(r.terms_days),
            "pct31_pm": pm,
            "oldest": int(r.oldest_open_days),
            "late12": None if pd.isna(r.avg_days_late_12m) else float(r.avg_days_late_12m),
            "signals": [s for s in (r.signal_1, r.signal_2, r.signal_3) if not pd.isna(s)],
        }
    return out


def page_data(df: pd.DataFrame) -> str:
    rows = []
    for r in df.itertuples():
        rows.append({
            "id": r.buyer_id,
            "name": r.buyer_name,
            "country": r.country_ko,
            "region": r.region,
            "pd_bp": int(r.pd_bp),
            "ar": int(r.open_ar_usd),
            "overdue": int(r.overdue_usd),
            "signal": None if pd.isna(r.signal_1) else r.signal_1,
        })
    regions = (df.groupby("region")["open_ar_usd"].sum()
               .sort_values(ascending=False, kind="stable").index.tolist())
    data = {"rows": rows, "regions": regions, "defaultLine": DEFAULT_LINE, "detail": top10_detail(df), "area": REGION_AREA}
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def css_root() -> str:
    return "\n".join(f"  --{k}: {v};" for k, v in TOKENS.items())


CSS = """
* { box-sizing: border-box; }
html, body { margin: 0; }
html { background: var(--color-bg); color-scheme: dark; }
body {
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-sans);
  font-size: var(--fs-md);
  line-height: 1.5;
  word-break: keep-all;
  overflow-wrap: break-word;
}
.wrap { max-width: var(--layout-max); margin: 0 auto; padding: var(--sp-6); }
.num { font-variant-numeric: tabular-nums; white-space: nowrap; }
h1, h2, p { margin: 0; color: var(--color-text); }

/* 머리: 제목과 기준일을 한 줄에, 아래 얇은 구분선 */
header {
  display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: var(--sp-1) var(--sp-4);
  padding-bottom: var(--sp-3); margin-bottom: var(--sp-4); border-bottom: 1px solid var(--color-border);
}
h1 { font-size: var(--fs-xl); font-weight: 700; line-height: 1.2; color: var(--color-text); }
.meta { font-size: var(--fs-sm); color: var(--color-text-muted); }

/* 판 */
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow);
  padding: var(--sp-4);
  min-width: 0;
  color: var(--color-text);
}
section { margin-bottom: var(--sp-4); }
h2 {
  font-size: var(--fs-lg); font-weight: 700; line-height: 1.2; color: var(--color-text);
  padding-bottom: var(--sp-2); margin-bottom: var(--sp-3); border-bottom: 1px solid var(--color-border);
}
.sub { font-size: var(--fs-sm); color: var(--color-text-muted); }

/* KPI */
.kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--sp-3); }
.kpi {
  background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-md);
  padding: var(--sp-3) var(--sp-4); min-width: 0; color: var(--color-text);
}
.kpi-label { font-size: var(--fs-sm); font-weight: 500; color: var(--color-text-muted); }
.kpi-num {
  display: block; overflow: hidden;
  margin: var(--sp-1) 0;
  font-size: var(--fs-2xl); font-weight: 700; line-height: 1.2; color: var(--color-text);
}
.kpi-num.shrink { font-size: var(--fs-xl); }
.kpi.focus { border-color: var(--grade-c); }
.kpi.focus .kpi-num { color: var(--grade-c); }

/* 등급 분포 + 슬라이더 */
.split { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: var(--sp-3); }
.gbar { display: flex; height: var(--sp-6); border-radius: var(--radius-sm); overflow: hidden; margin-bottom: var(--sp-3); }
.gseg {
  display: flex; align-items: center; padding: 0 var(--sp-2);
  color: var(--grade-on); font-size: var(--fs-xs); font-weight: 700; overflow: hidden; white-space: nowrap;
}
.legend { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 var(--sp-4); }
.legend-row {
  display: flex; align-items: center; gap: var(--sp-2); padding: var(--sp-1) 0;
  border-bottom: 1px solid var(--color-border); font-size: var(--fs-sm); color: var(--color-text);
}
.legend-row .amt { margin-left: auto; color: var(--color-text); }
.chip {
  display: inline-block; min-width: var(--sp-6); padding: 0 var(--sp-2);
  border-radius: var(--radius-sm); text-align: center;
  color: var(--grade-on); font-size: var(--fs-xs); font-weight: 700; line-height: 1.5;
}
.g-S { background: var(--grade-s); } .g-A { background: var(--grade-a); }
.g-B { background: var(--grade-b); } .g-C { background: var(--grade-c); }

.slider-head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-2); }
.slider-head label { font-size: var(--fs-sm); font-weight: 500; color: var(--color-text-muted); }
.line-val { font-size: var(--fs-xl); font-weight: 700; line-height: 1.2; color: var(--color-accent); }
input[type=range] { width: 100%; margin: var(--sp-3) 0 var(--sp-1); accent-color: var(--color-accent); }
input[type=range]:focus-visible { outline: var(--focus-ring) solid var(--color-accent); outline-offset: var(--sp-1); }
.range-ends { display: flex; justify-content: space-between; font-size: var(--fs-xs); color: var(--color-text-muted); }
.delta { margin-top: var(--sp-3); font-size: var(--fs-sm); color: var(--color-text); }
.delta b { color: var(--color-accent); }
.rule { margin-top: var(--sp-2); font-size: var(--fs-xs); color: var(--color-text-muted); }

/* 위험 상위 10 */
table { width: 100%; border-collapse: collapse; font-size: var(--fs-sm); color: var(--color-text); }
th {
  text-align: left; font-size: var(--fs-xs); font-weight: 500; color: var(--color-text-muted);
  padding: var(--sp-1) var(--sp-3); border-bottom: 1px solid var(--color-border); white-space: nowrap;
}
th:first-child, td:first-child { padding-left: 0; }
th:last-child, td:last-child { padding-right: 0; }
td { padding: var(--sp-2) var(--sp-3); border-bottom: 1px solid var(--color-border); color: var(--color-text); vertical-align: top; }
tr:last-child td { border-bottom: 0; }
th.r, td.r { text-align: right; }
td.rank { color: var(--color-text-muted); }
td.sig { color: var(--color-text-muted); }
.cards { display: none; }

/* 상세 패널(7절 ①) */
.hint { margin: calc(-1 * var(--sp-1)) 0 var(--sp-3); font-size: var(--fs-xs); color: var(--color-text-muted); }
.top-wrap.open { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: var(--sp-4); align-items: start; }
.pick { cursor: pointer; }
.pick:hover, .pick.sel { background: var(--color-bg); }
.pick:focus-visible { outline: var(--focus-ring) solid var(--color-accent); outline-offset: calc(-1 * var(--focus-ring)); }
.done-tag {
  display: inline-block; margin-left: var(--sp-2); padding: 0 var(--sp-1);
  border: 1px solid var(--color-accent); border-radius: var(--radius-sm);
  font-size: var(--fs-xs); font-weight: 500; line-height: 1.5; color: var(--color-accent); white-space: nowrap;
}
.detail[hidden] { display: none; }
.detail {
  min-width: 0; padding: var(--sp-4); background: var(--color-bg); color: var(--color-text);
  border: 1px solid var(--color-border); border-radius: var(--radius-md);
}
.detail-head { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--sp-3); margin-bottom: var(--sp-3); }
.detail h3 { margin: 0; font-size: var(--fs-lg); font-weight: 700; line-height: 1.2; color: var(--color-text); }
.detail h4 { margin: var(--sp-4) 0 var(--sp-1); font-size: var(--fs-sm); font-weight: 500; color: var(--color-text-muted); }
.facts { margin: 0; }
.facts div { display: flex; justify-content: space-between; gap: var(--sp-3); padding: var(--sp-1) 0; border-bottom: 1px solid var(--color-border); }
.facts dt { font-size: var(--fs-sm); color: var(--color-text-muted); }
.facts dd { margin: 0; font-size: var(--fs-sm); color: var(--color-text); text-align: right; }
.signals { margin: 0; padding-left: var(--sp-4); font-size: var(--fs-sm); color: var(--color-text); }
.signals li { padding: var(--sp-1) 0; }
.caveat { margin-top: var(--sp-2); font-size: var(--fs-sm); color: var(--color-text-muted); }
.btn {
  font: inherit; font-size: var(--fs-sm); font-weight: 500; line-height: 1.5; cursor: pointer;
  color: var(--color-text); background: transparent;
  border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: var(--sp-1) var(--sp-3);
}
.btn:focus-visible { outline: var(--focus-ring) solid var(--color-accent); outline-offset: var(--focus-ring); }
.btn.check { display: block; width: 100%; margin-top: var(--sp-4); padding: var(--sp-2) var(--sp-3); color: var(--color-accent); border-color: var(--color-accent); }
.btn.check.done { color: var(--color-bg); background: var(--color-accent); }

/* 지역별 채권 */
.reg { display: grid; grid-template-columns: minmax(0, var(--label-col)) minmax(0, 1fr) auto; align-items: center; gap: var(--sp-1) var(--sp-3); padding: var(--sp-2) 0; border-bottom: 1px solid var(--color-border); }
.reg-name { font-size: var(--fs-sm); color: var(--color-text); }
.track { height: var(--sp-2); border-radius: var(--radius-sm); overflow: hidden; }
.track-in { display: flex; height: 100%; }
.track-c { background: var(--grade-c); }
.track-rest { background: var(--color-border); }
.reg-amt { text-align: right; font-size: var(--fs-sm); color: var(--color-text); }
.reg-amt .sub { display: block; font-size: var(--fs-xs); color: var(--color-text-muted); }
.reg-key { display: flex; gap: var(--sp-4); margin-top: var(--sp-3); font-size: var(--fs-xs); color: var(--color-text-muted); }
.key { display: inline-block; width: var(--sp-3); height: var(--sp-3); border-radius: var(--radius-sm); vertical-align: middle; margin-right: var(--sp-1); }

/* 지역 타일 · 히트맵(7절 ③) */
.sub-h { margin: var(--sp-4) 0 var(--sp-1); font-size: var(--fs-md); font-weight: 700; line-height: 1.2; color: var(--color-text); }
.tiles {
  display: grid; gap: var(--sp-2);
  grid-template-columns: repeat(4, minmax(0, 1fr));
  grid-template-areas: "na we ce ea" "na me me sa";
}
.tile { min-width: 0; padding: var(--sp-3); border-radius: var(--radius-md); border: 1px solid var(--color-border); }
.tile p { margin: 0; color: inherit; }
.tile-name { font-size: var(--fs-sm); font-weight: 500; }
.tile-ar { margin: var(--sp-1) 0; font-size: var(--fs-lg); font-weight: 700; line-height: 1.2; }
.tile-sub { font-size: var(--fs-xs); }
.h-1 { background: var(--heat-c-1); color: var(--heat-c-on-1); }
.h-2 { background: var(--heat-c-2); color: var(--heat-c-on-2); }
.h-3 { background: var(--heat-c-3); color: var(--heat-c-on-3); }
.h-4 { background: var(--heat-c-4); color: var(--heat-c-on-4); }
.heat-key { display: flex; flex-wrap: wrap; gap: var(--sp-1) var(--sp-4); margin-top: var(--sp-2); font-size: var(--fs-xs); color: var(--color-text-muted); }
.heat-key .key { border: 1px solid var(--color-border); }
.heatmap { display: grid; grid-template-columns: minmax(0, var(--label-col)) repeat(4, minmax(0, 1fr)); gap: var(--sp-1); }
.hm-corner, .hm-head { padding: var(--sp-1) 0; }
.hm-head { text-align: right; }
.hm-row-name { display: flex; align-items: center; font-size: var(--fs-sm); color: var(--color-text); }
.hm-cell {
  display: flex; flex-direction: column; align-items: flex-end; justify-content: center; min-width: 0;
  padding: var(--sp-1) var(--sp-2); border-radius: var(--radius-sm); font-size: var(--fs-xs); line-height: 1.5;
}
.hm-n { font-weight: 700; }
.hm-cell.empty { background: var(--color-surface); color: var(--color-text-muted); border: 1px solid var(--color-border); }
.hm-cell.soft { color: var(--color-text); }
.hm-cell.full { color: var(--grade-on); }
.s-S { background: var(--grade-s-soft); } .s-A { background: var(--grade-a-soft); }
.s-B { background: var(--grade-b-soft); } .s-C { background: var(--grade-c-soft); }

footer { padding-top: var(--sp-3); border-top: 1px solid var(--color-border); font-size: var(--fs-xs); color: var(--color-text-muted); }

/* 경영진 한 장 단추 · 지금 선 글자(7절 ④) */
.toolbar { max-width: var(--layout-max); margin: 0 auto; padding: var(--sp-3) var(--sp-6) 0; display: flex; justify-content: flex-end; }
.print-line { display: none; margin-top: var(--sp-1); font-size: var(--fs-sm); font-weight: 700; color: var(--color-text); }

/* 휴대폰 폭: 640px 미만(design.md 2-7, @media에는 변수를 쓸 수 없음) */
@media (max-width: 639px) {
  .wrap { padding: var(--sp-4); }
  .card { padding: var(--sp-3); }
  .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--sp-2); }
  .kpi { padding: var(--sp-3); }
  .kpi-num { font-size: var(--fs-xl); }
  .kpi-num.shrink { font-size: var(--fs-lg); }
  .split { grid-template-columns: minmax(0, 1fr); gap: var(--sp-4); }
  .legend { grid-template-columns: minmax(0, 1fr); }
  table { display: none; }
  .cards { display: block; }
  .bcard { padding: var(--sp-3) 0; border-bottom: 1px solid var(--color-border); color: var(--color-text); }
  .bcard:last-child { border-bottom: 0; }
  .bcard-head { display: flex; align-items: flex-start; gap: var(--sp-2); }
  .bcard-rank { font-size: var(--fs-sm); color: var(--color-text-muted); }
  .bcard-name { flex: 1; min-width: 0; font-size: var(--fs-md); font-weight: 500; color: var(--color-text); }
  .bcard-meta { margin-top: var(--sp-1); font-size: var(--fs-sm); color: var(--color-text-muted); }
  .bcard-pair { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--sp-3); margin-top: var(--sp-2); }
  .bcard-pair .lab { display: block; font-size: var(--fs-xs); color: var(--color-text-muted); }
  .bcard-pair .val { font-size: var(--fs-md); color: var(--color-text); }
  .bcard-sig { margin-top: var(--sp-2); font-size: var(--fs-sm); color: var(--color-text-muted); }
  .reg { grid-template-columns: minmax(0, 1fr) auto; }
  .reg .track { grid-column: 1 / -1; grid-row: 2; }
  .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); grid-template-areas: "na ea" "we ce" "me sa"; }
  .heatmap { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .hm-corner { display: none; }
  .hm-row-name { grid-column: 1 / -1; margin-top: var(--sp-2); }
  .bcard.sel { background: var(--color-bg); }
  .top-wrap > .cards .detail { margin: var(--sp-2) 0 var(--sp-3); }
  .facts div { flex-wrap: wrap; }
  .toolbar { padding: var(--sp-3) var(--sp-4) 0; }
}
"""

# 경영진 한 장(7절 ④). 같은 규칙을 인쇄(@media print)와 화면의 '인쇄용 한 장 보기'(body.sheet)에 함께 쓴다.
# 색은 인쇄 토큰으로 바꿔 끼운다(흑백): 등급은 색 대신 글자 라벨과 굵기로 읽는다.
SHEET_VARS = """
  --color-bg: var(--print-bg); --color-surface: var(--print-bg); --color-border: var(--print-line);
  --color-text: var(--print-text); --color-text-muted: var(--print-muted); --color-accent: var(--print-text);
  --grade-s: var(--print-text); --grade-a: var(--print-text); --grade-b: var(--print-text); --grade-c: var(--print-text);
  --grade-on: var(--print-bg);
"""

SHEET_RULES = """
{S}.wrap { background: var(--color-bg); color: var(--color-text); }
{S}.panel-slider, {S}.map-extra, {S}.hint, {S}#detail, {S}.cards { display: none !important; }
{S}table { display: table; }
{S}.print-line { display: block; }
{S}header { margin-bottom: var(--sp-2); padding-bottom: var(--sp-2); }
{S}h1 { font-size: var(--fs-lg); }
{S}.print-line { font-size: var(--fs-xs); }
{S}section { margin-bottom: var(--sp-2); }
{S}.split { grid-template-columns: minmax(0, 1fr); }
{S}.kpis { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--sp-2); }
{S}.kpi, {S}.card { padding: var(--sp-2) var(--sp-3); }
{S}.kpi-num { font-size: var(--fs-xl); }
{S}.kpi-num.shrink { font-size: var(--fs-lg); }
{S}.kpi.focus { border: var(--focus-ring) solid var(--color-text); }
{S}.kpi.focus .kpi-num { color: var(--color-text); }
{S}h2 { font-size: var(--fs-md); margin-bottom: var(--sp-1); padding-bottom: var(--sp-1); }
{S}.gbar { height: var(--sp-4); margin-bottom: var(--sp-2); }
{S}.legend { grid-template-columns: repeat(4, minmax(0, 1fr)); }
{S}th, {S}td { padding: var(--sp-1) var(--sp-2); font-size: var(--fs-xs); line-height: 1.3; }
{S}td.sig { white-space: nowrap; }
{S}th:first-child, {S}td:first-child { padding-left: 0; }
{S}.reg { grid-template-columns: minmax(0, var(--label-col)) minmax(0, 1fr) auto; padding: var(--sp-1) 0; }
{S}.reg .track { grid-column: auto; grid-row: auto; }
{S}.reg-amt .sub { display: inline; margin-left: var(--sp-2); }
{S}.reg-name, {S}.reg-amt { line-height: 1.3; }
{S}.reg-key { margin-top: var(--sp-1); }
{S}.pick:hover, {S}.pick.sel { background: none; }
{S}.chip, {S}.gseg { background: none; color: var(--color-text); border: 1px solid var(--color-border); font-weight: 400; }
{S}.chip.g-B, {S}.gseg.g-B { font-weight: 500; }
{S}.chip.g-C, {S}.gseg.g-C { font-weight: 700; border: var(--focus-ring) solid var(--color-text); }
{S}.done-tag { border-color: var(--color-text); color: var(--color-text); }
{S}footer { padding-top: var(--sp-2); }
"""


def sheet_css() -> str:
    print_rules = SHEET_RULES.replace("{S}", "")
    sheet_rules = SHEET_RULES.replace("{S}", "body.sheet ")
    return f"""
/* 경영진 한 장(7절 ④): 인쇄 */
@page {{ size: A4 portrait; margin: 12mm; }}
@media print {{
  :root {{ {SHEET_VARS} }}
  html, body {{ background: var(--print-bg); -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  .toolbar {{ display: none !important; }}
  .wrap {{ max-width: none; padding: 0; }}
{print_rules}
}}
/* 경영진 한 장(7절 ④): 화면의 '인쇄용 한 장 보기' — A4 비율(210 : 297)의 흰 종이 */
body.sheet .wrap {{ {SHEET_VARS}
  max-width: var(--sheet-w); aspect-ratio: 210 / 297; margin: 0 auto var(--sp-6);
  padding: var(--sp-12); border: 1px solid var(--color-border); border-radius: 0;
}}
{sheet_rules}
"""


JS = """
const D = JSON.parse(document.getElementById('board-data').textContent);
const ROWS = D.rows;
const TOTAL_AR = ROWS.reduce((s, r) => s + r.ar, 0);
const TOP10 = ROWS.slice().sort((a, b) => b.pd_bp - a.pd_bp || (a.id < b.id ? -1 : 1)).slice(0, 10);

function gradeOf(bp, line) {
  if (bp >= 100 * line) return 'C';
  if (2 * bp >= 100 * line) return 'B';
  if (4 * bp >= 100 * line) return 'A';
  return 'S';
}
const usd = n => (n < 0 ? '\\u2212$' : '$') + Math.abs(n).toLocaleString('en-US');
const signedUsd = n => (n < 0 ? '\\u2212$' : '+$') + Math.abs(n).toLocaleString('en-US');
const signedN = n => (n < 0 ? '\\u2212' : '+') + Math.abs(n);
const pct = bp => (bp / 100).toFixed(1) + '%';
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cell = v => v === null || v === undefined ? '\\u2013' : esc(v);

function summarize(line) {
  const g = { S: { n: 0, ar: 0 }, A: { n: 0, ar: 0 }, B: { n: 0, ar: 0 }, C: { n: 0, ar: 0 } };
  const reg = {};
  D.regions.forEach(k => {
    reg[k] = { ar: 0, c: 0, n: 0, g: { S: { n: 0, ar: 0 }, A: { n: 0, ar: 0 }, B: { n: 0, ar: 0 }, C: { n: 0, ar: 0 } } };
  });
  ROWS.forEach(r => {
    const gr = gradeOf(r.pd_bp, line);
    g[gr].n += 1; g[gr].ar += r.ar;
    const v = reg[r.region];
    v.ar += r.ar; v.n += 1; v.g[gr].n += 1; v.g[gr].ar += r.ar;
    if (gr === 'C') v.c += r.ar;
  });
  return { g, reg };
}
const BASE = summarize(D.defaultLine);
const OVERDUE = ROWS.filter(r => r.overdue > 0);
const OVERDUE_SUM = OVERDUE.reduce((s, r) => s + r.overdue, 0);

function renderKpis(s) {
  const c = s.g.C;
  document.getElementById('kpis').innerHTML = [
    ['위험 바이어 (C등급)', c.n + '곳', '위험 선 이상인 바이어', false],
    ['C등급 채권', usd(c.ar), '전체 채권의 ' + (c.ar / TOTAL_AR * 100).toFixed(1) + '%', true],
    ['전체 채권', usd(TOTAL_AR), ROWS.length + '곳 합계', false],
    ['연체 금액', usd(OVERDUE_SUM), '연체가 있는 곳 ' + OVERDUE.length + '곳', false],
  ].map(([t, v, sub, focus]) =>
    `<div class="kpi${focus ? ' focus' : ''}"><p class="kpi-label">${t}</p>` +
    `<span class="kpi-num num fit">${v}</span><p class="sub">${sub}</p></div>`).join('');
}

function renderGrades(s) {
  const segs = ['S', 'A', 'B', 'C'].filter(k => s.g[k].n > 0).map(k => {
    const w = s.g[k].n / ROWS.length * 100;
    const lab = w >= 8 ? `${k} ${s.g[k].n}곳` : '';
    return `<div class="gseg g-${k}" style="width:${w}%" title="${k}등급 ${s.g[k].n}곳">${lab}</div>`;
  }).join('');
  document.getElementById('gbar').innerHTML = segs;
  document.getElementById('legend').innerHTML = ['S', 'A', 'B', 'C'].map(k =>
    `<div class="legend-row"><span class="chip g-${k}">${k}</span>` +
    `<span class="num">${s.g[k].n}곳</span><span class="amt num">${usd(s.g[k].ar)}</span></div>`).join('');
}

function renderDelta(line, s) {
  document.getElementById('line-val').textContent = line + '%';
  const dn = s.g.C.n - BASE.g.C.n, dar = s.g.C.ar - BASE.g.C.ar;
  document.getElementById('delta').innerHTML =
    `처음 ${D.defaultLine}%보다 C등급 <b class="num">${signedN(dn)}곳</b> · <b class="num">${signedUsd(dar)}</b>`;
}

// 상세 패널(7절 ①): 상태는 이 페이지 안의 변수에만 둔다(보내거나 저장하지 않음, 새로 고침하면 처음으로).
let openId = null;
const checked = {};  // buyer_id → '시:분'
const PANEL = document.getElementById('detail');
const MOBILE = window.matchMedia('(max-width: 639px)');
const doneTag = id => checked[id] ? '<span class="done-tag">확인 완료</span>' : '';

function renderTop(line) {
  const body = TOP10.map((r, i) => {
    const g = gradeOf(r.pd_bp, line);
    const sel = r.id === openId;
    return `<tr class="pick${sel ? ' sel' : ''}" data-id="${r.id}" tabindex="0" aria-expanded="${sel}" aria-controls="detail">` +
      `<td class="rank num">${i + 1}</td><td>${esc(r.name)}${doneTag(r.id)}</td><td>${esc(r.country)}</td>` +
      `<td><span class="chip g-${g}">${g}</span></td><td class="r num">${pct(r.pd_bp)}</td>` +
      `<td class="r num">${usd(r.ar)}</td><td class="r num">${usd(r.overdue)}</td><td class="sig">${cell(r.signal)}</td></tr>`;
  }).join('');
  document.getElementById('top-body').innerHTML = body;
  document.getElementById('top-cards').innerHTML = TOP10.map((r, i) => {
    const g = gradeOf(r.pd_bp, line);
    const sel = r.id === openId;
    return `<div class="bcard pick${sel ? ' sel' : ''}" data-id="${r.id}" tabindex="0" role="button" aria-expanded="${sel}" aria-controls="detail">` +
      `<div class="bcard-head"><span class="bcard-rank num">${i + 1}</span>` +
      `<span class="bcard-name">${esc(r.name)}${doneTag(r.id)}</span><span class="chip g-${g}">${g}</span></div>` +
      `<p class="bcard-meta">${esc(r.country)} · 위험 점수 <span class="num">${pct(r.pd_bp)}</span></p>` +
      `<div class="bcard-pair"><div><span class="lab">채권</span><span class="val num">${usd(r.ar)}</span></div>` +
      `<div><span class="lab">연체</span><span class="val num">${usd(r.overdue)}</span></div></div>` +
      `<p class="bcard-sig">${cell(r.signal)}</p></div>`;
  }).join('');
}

function renderDetail(line) {
  const wrap = document.getElementById('top-wrap');
  if (!openId) { PANEL.hidden = true; wrap.classList.remove('open'); return; }
  const r = ROWS.find(x => x.id === openId), d = D.detail[openId];
  const g = gradeOf(r.pd_bp, line);
  const days = v => v === null ? '\\u2013' : v + '일';
  const fields = [
    ['나라', esc(r.country)], ['지역', esc(r.region)], ['업종', esc(d.industry)], ['결제방식', esc(d.payment)],
    ['결제기간', `<span class="num">${days(d.terms)}</span>`],
    ['채권', `<span class="num">${usd(r.ar)}</span>`], ['연체', `<span class="num">${usd(r.overdue)}</span>`],
    ['기일을 31일 넘긴 채권 비중', `<span class="num">${d.pct31_pm === null ? '\\u2013' : (d.pct31_pm / 10).toFixed(1) + '%'}</span>`],
    ['가장 오래 밀린 인보이스의 연체일', `<span class="num">${days(d.oldest)}</span>`],
    ['최근 1년 평균 지연일', `<span class="num">${d.late12 === null ? '\\u2013' : d.late12.toFixed(1) + '일'}</span>`],
    ['위험 점수', `<span class="num">${pct(r.pd_bp)}</span>`],
    [`등급 (지금 선 ${line}%)`, `<span class="chip g-${g}">${g}</span>`],
  ];
  const t = checked[openId];
  PANEL.innerHTML =
    `<div class="detail-head"><h3 id="detail-title">${esc(r.name)}</h3>` +
    `<button type="button" class="btn" data-act="close">닫기</button></div>` +
    `<dl class="facts">${fields.map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join('')}</dl>` +
    `<h4>위험 신호</h4><ul class="signals">${d.signals.map(s => `<li>${esc(s)}</li>`).join('')}</ul>` +
    `<p class="caveat">이 신호들은 확인해 볼 이유이지, 연체의 원인이라는 뜻은 아닙니다.</p>` +
    `<button type="button" class="btn check${t ? ' done' : ''}" data-act="check" aria-pressed="${!!t}">${t ? '확인 완료 · ' + t : '확인 필요'}</button>`;
  PANEL.hidden = false;
  placePanel();
}

// 넓은 화면은 표 오른쪽 칸, 휴대폰 폭은 누른 카드 바로 아래.
function placePanel() {
  const wrap = document.getElementById('top-wrap');
  if (!openId) return;
  if (MOBILE.matches) {
    wrap.classList.remove('open');
    const card = document.querySelector(`#top-cards .bcard[data-id="${openId}"]`);
    if (card && card.nextSibling !== PANEL) card.after(PANEL);
  } else {
    wrap.classList.add('open');
    if (PANEL.parentNode !== wrap) wrap.appendChild(PANEL);
  }
}

function openDetail(id) {
  openId = openId === id ? null : id;
  render();
  if (openId) PANEL.querySelector('[data-act="close"]').focus();
}
function closeDetail() {
  const id = openId;
  openId = null;
  render();
  const back = document.querySelector(`${MOBILE.matches ? '#top-cards' : '#top-body'} [data-id="${id}"]`);
  if (back) back.focus();
}
function toggleCheck() {
  if (checked[openId]) { delete checked[openId]; }
  else {
    const now = new Date();
    checked[openId] = String(now.getHours()).padStart(2, '0') + ':' + String(now.getMinutes()).padStart(2, '0');
  }
  render();
  PANEL.querySelector('[data-act="check"]').focus();
}

['top-body', 'top-cards'].forEach(boxId => {
  const box = document.getElementById(boxId);
  box.addEventListener('click', e => {
    const el = e.target.closest('.pick');
    if (el) openDetail(el.dataset.id);
  });
  box.addEventListener('keydown', e => {
    const el = e.target.closest('.pick');
    if (el && e.target === el && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); openDetail(el.dataset.id); }
  });
});
PANEL.addEventListener('click', e => {
  e.stopPropagation();
  const act = e.target.closest('[data-act]');
  if (!act) return;
  if (act.dataset.act === 'close') closeDetail();
  if (act.dataset.act === 'check') toggleCheck();
});
PANEL.addEventListener('keydown', e => { if (e.key === 'Escape') closeDetail(); });

function renderRegions(s) {
  const max = Math.max(...D.regions.map(k => s.reg[k].ar));
  document.getElementById('regions').innerHTML = D.regions.map(k => {
    const v = s.reg[k], w = v.ar / max * 100;
    const cw = v.ar ? v.c / v.ar * 100 : 0;
    return `<div class="reg"><span class="reg-name">${esc(k)}</span>` +
      `<div class="track" role="img" aria-label="${esc(k)} 채권 ${usd(v.ar)}, 그중 C등급 ${usd(v.c)}">` +
      `<div class="track-in" style="width:${w}%"><div class="track-c" style="width:${cw}%"></div><div class="track-rest" style="flex:1"></div></div></div>` +
      `<span class="reg-amt num">${usd(v.ar)}<span class="sub">C등급 ${usd(v.c)}</span></span></div>`;
  }).join('');
}

// 지역 타일 · 히트맵(7절 ③)
// 타일 진하기 = 지역 채권 중 C등급 채권 비중: 1단계 10% 미만 · 2단계 10–25% · 3단계 25–50% · 4단계 50% 이상
function heatStep(c, ar) {
  if (!ar) return 1;
  const r = c / ar;
  return r >= 0.5 ? 4 : r >= 0.25 ? 3 : r >= 0.1 ? 2 : 1;
}
function renderMap(s) {
  document.getElementById('tiles').innerHTML = D.regions.map(k => {
    const v = s.reg[k], st = heatStep(v.c, v.ar);
    const share = v.ar ? (v.c / v.ar * 100).toFixed(1) + '%' : '\\u2013';
    return `<div class="tile h-${st}" style="grid-area:${D.area[k]}">` +
      `<p class="tile-name">${esc(k)}</p>` +
      `<p class="tile-ar num">${usd(v.ar)}</p>` +
      `<p class="tile-sub"><span class="num">${v.n}곳</span></p>` +
      `<p class="tile-sub">C등급 <span class="num">${usd(v.c)}</span> · <span class="num">${share}</span></p></div>`;
  }).join('');
  // 히트맵 칸 진하기 = 그 지역 채권 중 이 칸(등급)의 몫: 0곳은 빈칸 · 3분의 1 미만은 연하게 · 3분의 1 이상은 진하게
  const head = '<div class="hm-corner"></div>' + ['S', 'A', 'B', 'C'].map(k => `<div class="hm-head"><span class="chip g-${k}">${k}</span></div>`).join('');
  const rows = D.regions.map(k => {
    const v = s.reg[k];
    const cells = ['S', 'A', 'B', 'C'].map(gk => {
      const c = v.g[gk];
      const lv = c.n === 0 ? 'empty' : (v.ar > 0 && 3 * c.ar >= v.ar ? `full g-${gk}` : `soft s-${gk}`);
      const body = c.n === 0 ? '<span class="hm-n">\\u2013</span>' :
        `<span class="hm-n num">${c.n}곳</span><span class="hm-ar num">${usd(c.ar)}</span>`;
      return `<div class="hm-cell ${lv}" aria-label="${esc(k)} ${gk}등급 ${c.n}곳 ${usd(c.ar)}">${body}</div>`;
    }).join('');
    return `<div class="hm-row-name">${esc(k)}</div>${cells}`;
  }).join('');
  document.getElementById('heatmap').innerHTML = head + rows;
}

function fitNumbers() {
  document.querySelectorAll('.fit').forEach(el => {
    el.classList.remove('shrink');
    if (el.scrollWidth > el.clientWidth) el.classList.add('shrink');
  });
}

function render() {
  const line = Number(document.getElementById('line').value);
  const s = summarize(line);
  renderKpis(s); renderGrades(s); renderDelta(line, s); renderTop(line); renderDetail(line); renderRegions(s); renderMap(s);
  document.getElementById('print-line').textContent =
    `위험 선 ${line}% 기준 · 선 이상 C · 선의 절반 이상 B · 4분의 1 이상 A · 나머지 S`;
  fitNumbers();
}

// 경영진 한 장(7절 ④): 화면에서도 인쇄할 구역만 A4 비율로 보여 주고, 다시 누르면 되돌아간다.
const SHEET_BTN = document.getElementById('sheet-btn');
SHEET_BTN.addEventListener('click', () => {
  const on = document.body.classList.toggle('sheet');
  SHEET_BTN.textContent = on ? '화면 보기로 돌아가기' : '인쇄용 한 장 보기';
  SHEET_BTN.setAttribute('aria-pressed', String(on));
  fitNumbers();
  window.scrollTo(0, 0);
});
window.addEventListener('beforeprint', fitNumbers);
document.getElementById('line').addEventListener('input', render);
window.addEventListener('resize', fitNumbers);
MOBILE.addEventListener('change', placePanel);
if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitNumbers);
render();
"""


def build_html(data_json: str) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>바이어 리스크 한눈에</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;700&display=swap">
<style>
:root {{
{css_root()}
}}
{CSS}
{sheet_css()}
</style>
</head>
<body>
<div class="toolbar">
  <button type="button" class="btn" id="sheet-btn" aria-pressed="false">인쇄용 한 장 보기</button>
</div>
<div class="wrap">
  <header>
    <div>
      <h1>바이어 리스크 한눈에</h1>
      <p class="print-line" id="print-line"></p>
    </div>
    <p class="meta">기준일 {REF_DATE} · (가상) 한빛정밀(주) 바이어 150곳 · 합성 데이터</p>
  </header>

  <section aria-label="핵심 숫자">
    <div class="kpis" id="kpis"></div>
  </section>

  <section class="split">
    <div class="card">
      <h2>신호등 등급 분포</h2>
      <div class="gbar" id="gbar" role="img" aria-label="등급별 곳 수 막대"></div>
      <div class="legend" id="legend"></div>
    </div>
    <div class="card panel-slider">
      <div class="slider-head">
        <label for="line">위험 선 (위험 점수)</label>
        <span class="line-val num" id="line-val">{DEFAULT_LINE}%</span>
      </div>
      <input type="range" id="line" min="5" max="30" step="1" value="{DEFAULT_LINE}">
      <div class="range-ends"><span>5%</span><span>30%</span></div>
      <p class="delta" id="delta"></p>
      <p class="rule">선 이상 C · 선의 절반 이상 B · 4분의 1 이상 A · 나머지 S</p>
    </div>
  </section>

  <section class="card">
    <h2>이번 주 전화할 곳 · 위험 상위 10</h2>
    <p class="hint">줄을 누르면 확인해 볼 이유가 열립니다. 확인 여부는 사람이 단추로 남깁니다.</p>
    <div class="top-wrap" id="top-wrap">
      <table>
        <thead><tr><th>순위</th><th>바이어 이름</th><th>나라</th><th>등급</th><th class="r">위험 점수</th><th class="r">채권</th><th class="r">연체</th><th>위험 신호</th></tr></thead>
        <tbody id="top-body"></tbody>
      </table>
      <div class="cards" id="top-cards"></div>
      <div class="detail" id="detail" role="region" aria-labelledby="detail-title" hidden></div>
    </div>
  </section>

  <section class="card">
    <h2>지역별 채권</h2>
    <div id="regions"></div>
    <div class="reg-key"><span><i class="key track-c"></i>지금 C등급인 몫</span><span><i class="key track-rest"></i>나머지</span></div>

    <div class="map-extra">
    <h3 class="sub-h">지역 타일</h3>
    <p class="hint">대략의 지리 배치입니다. 타일이 진할수록 그 지역 채권 중 지금 C등급인 몫이 큽니다.</p>
    <div class="tiles" id="tiles"></div>
    <div class="heat-key" aria-label="타일 진하기 범례">
      <span><i class="key h-1"></i>10% 미만</span><span><i class="key h-2"></i>10–25%</span>
      <span><i class="key h-3"></i>25–50%</span><span><i class="key h-4"></i>50% 이상</span>
    </div>

    <h3 class="sub-h">지역 × 등급</h3>
    <p class="hint">칸마다 곳 수와 채권입니다. 그 지역 채권의 3분의 1 이상이 몰린 칸은 진하게, 0곳은 '–'입니다.</p>
    <div class="heatmap" id="heatmap"></div>
    </div>
  </section>

  <footer>(가상) 합성 데이터 · 기준일 {REF_DATE} · 위험 점수는 판단을 돕는 값이고 결정은 사람이 합니다</footer>
</div>
<script id="board-data" type="application/json">{data_json}</script>
<script>
{JS}
</script>
</body>
</html>
"""


def main() -> None:
    df = load()
    report(df)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_html(page_data(df)), encoding="utf-8", newline="\n")
    print(f"\n저장: {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
