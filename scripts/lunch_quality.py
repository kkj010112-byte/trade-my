"""3일차 실습 C: 한빛식당(가상) 점심 기록 데이터 진단 — 어디가 얼마나 엉망인지 센다 (원본은 읽기만).

실행: uv run python scripts/lunch_quality.py
결과: workbench/day3/outputs/lunch_quality.md
근거: labs/day3/lab-c/lab_c_guide.md 「3. 데이터 진단」. 고치지 않고 세기만 한다(정제는 「4」).
"""
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
SRC = "labs/day3/lab-c/hanbit_lunch_log.csv"
OUT = Path("workbench/day3/outputs/lunch_quality.md")

df = pd.read_csv(SRC, encoding="utf-8-sig", dtype=str, keep_default_na=False)
df.insert(0, "줄", range(2, len(df) + 2))  # 원본 파일의 줄 번호(머리줄 = 1)

WEEKDAYS = "월화수목금토일"
STD_WEEKDAY = set("월화수목금")
STD_WEATHER = {"맑음", "흐림", "비", "눈"}
MENU_VARIANTS = ["돈까스", "카레라이스", "제육", "치킨마요덮밥", "김치 찌개"]  # 「4」 R9 왼쪽
EVENT_VARIANTS = ["외부손님", "전사교육"]
EN_WEEKDAY = {"Mon": "월", "Tue": "화", "Wed": "수", "Thu": "목", "Fri": "금"}

DATE_FORMATS = [  # (이름, 정규식) — 진단용 해석만, 원본은 바꾸지 않는다
    ("YYYY-MM-DD", r"^(\d{4})-(\d{1,2})-(\d{1,2})$"),
    ("YYYY/MM/DD", r"^(\d{4})/(\d{1,2})/(\d{1,2})$"),
    ("YYYY.M.D", r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$"),
    ("M월 D일", r"^(\d{1,2})월\s*(\d{1,2})일$"),
]


def parse_date(s):
    s = s.strip()
    for name, pat in DATE_FORMATS:
        m = re.match(pat, s)
        if not m:
            continue
        if name == "M월 D일":  # 연도 없음: 10–12월은 2025년, 1–9월은 2026년
            mo, d = int(m[1]), int(m[2])
            return name, date(2025 if mo >= 10 else 2026, mo, d)
        return name, date(int(m[1]), int(m[2]), int(m[3]))
    return "알 수 없음", None


parsed = df["날짜"].map(parse_date)
df["_형식"] = parsed.map(lambda t: t[0])
df["_날짜"] = parsed.map(lambda t: t[1])
holiday = df["비고"].eq("휴무")


def written_weekday(s):
    s = s.strip()
    return EN_WEEKDAY.get(s, s[:1] if s else "")


def to_num(s):
    return pd.to_numeric(s, errors="coerce")


attend, meals = to_num(df["출근예정"]), to_num(df["식수"])

# ── 종류별 표시(True = 엉망) ──────────────────────────────────
checks = {}
checks["날짜 형식 섞임"] = df["_형식"].ne("YYYY-MM-DD")
checks["요일 표기 섞임"] = ~df["요일"].isin(STD_WEEKDAY)
checks["같은 날짜가 두 줄"] = df["_날짜"].notna() & df["_날짜"].duplicated(keep=False)
checks["휴무 줄"] = holiday
checks["식수 빈칸"] = df["식수"].eq("")
checks["불가능해 보이는 식수"] = (
    ~holiday & meals.notna() & attend.notna() & ((meals > attend) | (meals < attend * 0.2))
)
checks["날씨 표기 섞임(표준 4개 아닌 값)"] = ~holiday & df["날씨"].ne("") & ~df["날씨"].isin(STD_WEATHER)
checks["날씨 빈칸(휴무 아닌 줄)"] = ~holiday & df["날씨"].eq("")
checks["최고기온 단위(℃ · °C) 붙음"] = df["최고기온"].str.contains("℃|°C", regex=True)
checks["최고기온 빈칸(휴무 아닌 줄)"] = ~holiday & df["최고기온"].eq("")
checks["메뉴 이름 섞임"] = df["메인메뉴"].isin(MENU_VARIANTS)
checks["행사 이름 섞임"] = df["행사"].isin(EVENT_VARIANTS)
checks["출근예정 빈칸"] = df["출근예정"].eq("")
actual_wd = df["_날짜"].map(lambda d: WEEKDAYS[d.weekday()] if d else "")
checks["(참고) 적힌 요일이 실제 요일과 다름"] = df["_날짜"].notna() & (
    df["요일"].map(written_weekday) != actual_wd
)

SHOW_COL = {  # 예시에 보일 원본 열
    "날짜 형식 섞임": ["날짜"],
    "요일 표기 섞임": ["날짜", "요일"],
    "같은 날짜가 두 줄": ["날짜", "식수", "비고"],
    "휴무 줄": ["날짜", "비고"],
    "식수 빈칸": ["날짜", "식수", "비고"],
    "불가능해 보이는 식수": ["날짜", "출근예정", "식수"],
    "날씨 표기 섞임(표준 4개 아닌 값)": ["날짜", "날씨"],
    "날씨 빈칸(휴무 아닌 줄)": ["날짜", "날씨"],
    "최고기온 단위(℃ · °C) 붙음": ["날짜", "최고기온"],
    "최고기온 빈칸(휴무 아닌 줄)": ["날짜", "최고기온"],
    "메뉴 이름 섞임": ["날짜", "메인메뉴"],
    "행사 이름 섞임": ["날짜", "행사"],
    "출근예정 빈칸": ["날짜", "출근예정"],
    "(참고) 적힌 요일이 실제 요일과 다름": ["날짜", "요일"],
}


def example(row, cols):
    parts = [f"{c} `{row[c]}`" if row[c] != "" else f"{c} (빈칸)" for c in cols]
    return f"{row['줄']}줄: " + " · ".join(parts)


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]
    return "\n".join(out)


lines = ["# 한빛식당(가상) 점심 기록 데이터 진단", ""]
lines += [f"- 원본: `{SRC}` (읽기만, 고치지 않음)", "- 만든 코드: `scripts/lunch_quality.py`", ""]

# 1. 기본
dmin, dmax = df["_날짜"].dropna().min(), df["_날짜"].dropna().max()
lines += ["## 1. 줄 수 · 열 이름 · 날짜 범위", ""]
lines += [f"- 줄 수: **{len(df)}줄** (머리줄 제외)"]
lines += [f"- 열 이름({len(df.columns) - 3}개): " + " · ".join(c for c in df.columns if not c.startswith("_") and c != "줄")]
lines += [f"- 날짜 범위: **{dmin} ~ {dmax}** (진단용으로만 날짜를 해석, 해석 못 한 줄 {df['_날짜'].isna().sum()}개)", ""]

# 2. 엉망 종류별 표
lines += ["## 2. 엉망인 곳 — 종류별", "", "예시는 파일에서 먼저 나온 2줄, 값은 원본 글자 그대로입니다.", ""]
rows = []
for kind, mask in checks.items():
    hit = df[mask]
    ex = " / ".join(example(r, SHOW_COL[kind]) for _, r in hit.head(2).iterrows()) or "-"
    rows.append([kind, len(hit), ex])
lines += [md_table(["종류", "줄 수", "예시 2개"], rows), ""]

# 세부
fmt_counts = df["_형식"].value_counts()
lines += ["### 세부", ""]
lines += ["- 날짜 형식별 줄 수: " + " · ".join(f"`{k}` {v}" for k, v in fmt_counts.items())]
wd_counts = df.loc[checks["요일 표기 섞임"], "요일"].value_counts()
lines += ["- 요일 표기(한 글자 아닌 것): " + " · ".join(f"`{k}` {v}" for k, v in wd_counts.items())]
wx_counts = df.loc[checks["날씨 표기 섞임(표준 4개 아닌 값)"], "날씨"].value_counts()
lines += ["- 날씨 표기(표준 4개 아닌 것): " + " · ".join(f"`{k}` {v}" for k, v in wx_counts.items())]
unit_counts = df["최고기온"].str.extract(r"(\s*℃|\s*°C)$")[0].dropna().map(lambda u: f"숫자{u}").value_counts()
lines += ["- 최고기온 단위 모양: " + " · ".join(f"`{k}` {v}" for k, v in unit_counts.items())]
mn = df.loc[checks["메뉴 이름 섞임"], "메인메뉴"].value_counts()
ev = df.loc[checks["행사 이름 섞임"], "행사"].value_counts()
lines += ["- 메뉴 다른 이름: " + " · ".join(f"`{k}` {v}" for k, v in mn.items())]
lines += ["- 행사 다른 이름: " + " · ".join(f"`{k}` {v}" for k, v in ev.items())]
dup = df[checks["같은 날짜가 두 줄"]].copy()
lines += [f"- 같은 날짜가 두 줄: 날짜 {dup['_날짜'].nunique()}개 · 줄 {len(dup)}개", ""]
dup_rows = []
for d, g in dup.groupby("_날짜", sort=True):
    same = g.drop(columns=["줄"]).drop_duplicates().shape[0] == 1
    has_re = g["비고"].str.contains("재집계").any()
    note = "완전히 같은 줄" if same else ("식수 다름 · `재집계` 줄 있음" if has_re else "내용 다름")
    dup_rows.append([d, ", ".join(str(x) for x in g["줄"]), " / ".join(g["식수"]), note])
lines += [md_table(["날짜", "원본 줄", "식수", "모양"], dup_rows), ""]
wrong = df[checks["(참고) 적힌 요일이 실제 요일과 다름"]]
lines += ["- (참고) 적힌 요일이 실제와 다른 줄: " + " · ".join(
    f"{r['줄']}줄 `{r['날짜']}` 적힘 `{r['요일']}` → 실제 {actual_wd[i]}" for i, r in wrong.iterrows())]
lines += ["  - `월요일` · `Mon`처럼 표기만 다른 줄은 여기 넣지 않았습니다. 정제 R2에서 날짜로 다시 계산합니다.", ""]

# 3. 비고
memo = df.loc[df["비고"].ne(""), "비고"].value_counts()
lines += ["## 3. 비고 열에 나오는 글", ""]
lines += [md_table(["비고 (원본 그대로)", "줄 수"], [[f"`{k}`", v] for k, v in memo.items()])]
lines += ["", f"- 비고가 빈칸인 줄: {df['비고'].eq('').sum()}줄", ""]

# 4. 사람이 정할 줄
dec = df[checks["불가능해 보이는 식수"]]
lines += ["## 4. 사람이 정해야 할 줄", ""]
lines += ["식수가 출근예정보다 많거나 출근예정의 20% 미만인 줄입니다. 지울지 고칠지는 사람이 정합니다.", ""]
dec_rows = []
for _, r in dec.iterrows():
    a, m = int(r["출근예정"]), int(r["식수"])
    why = "식수 > 출근예정" if m > a else f"식수 < 출근예정의 20%({a * 0.2:g})"
    dec_rows.append([r["줄"], f"`{r['날짜']}`", a, m, f"`{r['비고']}`" if r["비고"] else "(빈칸)", why])
lines += [md_table(["원본 줄", "날짜", "출근예정", "식수", "비고", "까닭"], dec_rows), ""]
if dec["비고"].eq("수기 집계").any():
    lines += ["- 비고가 `수기 집계`인 줄은 정제 R6에서 **'뺀다' 또는 '×10 보정'** 중 하나를 수강생이 프롬프트에 적어 정합니다.",
              "  (×10이면 맞는 크기인지는 '확인 필요' — 이 진단은 고치지 않습니다.)"]
lines += ["- 휴무 줄(출근예정 0 · 식수 0)은 정제 R3에서 빠지므로 여기 넣지 않았습니다.", ""]

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines), encoding="utf-8")

print(f"줄 수 {len(df)} · 날짜 범위 {dmin} ~ {dmax}")
for kind, mask in checks.items():
    print(f"{kind}: {int(mask.sum())}")
print("사람이 정할 줄:")
print(dec[["줄", "날짜", "출근예정", "식수", "비고"]].to_string(index=False))
print(f"저장: {OUT}")
