"""3일차 실습 C: 한빛식당(가상) 점심 기록 정제 — lunch_rules.md 표 그대로 R1 → R9 순서로 적용 (원본은 읽기만).

실행: uv run python scripts/lunch_clean.py
결과: workbench/day3/outputs/lunch_clean.csv (UTF-8 BOM) · workbench/day3/outputs/lunch_clean_log.md
근거: workbench/day3/outputs/lunch_rules.md · labs/day3/lab-c/lab_c_guide.md 「4. 정제 규칙」
적용 순서: R1 · R2 · R3 · R4 · R5 · R10 · R6 · R7 · R8 · R9 (R10은 R6가 출근예정을 쓰므로 먼저)
"""
import math
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
SRC = "labs/day3/lab-c/hanbit_lunch_log.csv"
OUT_DIR = Path("workbench/day3/outputs")
OUT_CSV = OUT_DIR / "lunch_clean.csv"
OUT_LOG = OUT_DIR / "lunch_clean_log.md"

MANUAL_DECISION = "뺀다"  # 수강생 결정: '수기 집계' 줄 → 뺀다 ('×10 보정'이면 식수 × 10으로 남긴다)

WEEKDAYS = "월화수목금토일"
EN_WEEKDAY = {"Mon": "월", "Tue": "화", "Wed": "수", "Thu": "목", "Fri": "금"}
WEATHER_MAP = {
    "맑": "맑음", "sunny": "맑음",
    "구름많음": "흐림", "cloudy": "흐림",
    "rain": "비", "우천": "비", "소나기": "비", "흐리고 비": "비",
    "snow": "눈",
    "": "모름",
}
MENU_MAP = {"돈까스": "돈가스", "카레라이스": "카레", "제육": "제육볶음", "치킨마요덮밥": "치킨마요", "김치 찌개": "김치찌개"}
EVENT_MAP = {"외부손님": "외부 손님 방문", "전사교육": "전사 교육"}

df = pd.read_csv(SRC, encoding="utf-8-sig", dtype=str, keep_default_na=False)
COLS = list(df.columns)
n_start = len(df)
log = []  # (규칙, 할 일, 고친/뺀 줄 수, 남은 줄 수, 메모)


def record(rule, what, n, note=""):
    log.append((rule, what, n, len(df), note))
    print(f"{rule}: {what} {n}줄 → 남은 {len(df)}줄 {note}")


# R1 날짜를 YYYY-MM-DD로
def parse_date(s):
    s = s.strip()
    m = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", s)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3]))
    m = re.match(r"^(\d{1,2})월\s*(\d{1,2})일$", s)
    if m:  # 연도 없음: 10–12월은 2025년, 1–9월은 2026년
        mo = int(m[1])
        return date(2025 if mo >= 10 else 2026, mo, int(m[2]))
    raise ValueError(f"해석 못 한 날짜: {s!r}")


d = df["날짜"].map(parse_date)
iso = d.map(lambda x: x.isoformat())
n = int((iso != df["날짜"]).sum())
df["날짜"] = iso
record("R1", "날짜 형식 고침", n)

# R2 요일을 날짜에서 다시 계산 — 적힌 요일이 실제와 '달랐던' 줄만 센다
actual = d.map(lambda x: WEEKDAYS[x.weekday()])
written = df["요일"].str.strip().map(lambda s: EN_WEEKDAY.get(s, s[:1]))
wrong = written != actual
df["요일"] = actual
record("R2", "요일이 실제와 달랐던 줄 고침", int(wrong.sum()),
       "(" + ", ".join(df.loc[wrong, "날짜"]) + ")")

# R3 휴무 줄 빼기
mask = df["비고"].eq("휴무")
df = df[~mask]
record("R3", "휴무 줄 뺌", int(mask.sum()))

# R4 같은 날짜 두 줄 → '재집계' 줄, 없으면 나중 줄
df = df.reset_index(drop=True)
df["_재집계"] = df["비고"].str.contains("재집계")
df["_순서"] = range(len(df))
keep = df.sort_values(["날짜", "_재집계", "_순서"]).groupby("날짜").tail(1).index
n = len(df) - len(keep)
dropped_dates = sorted(df.loc[~df.index.isin(keep), "날짜"])
df = df.loc[sorted(keep)].drop(columns=["_재집계", "_순서"])
record("R4", "같은 날짜 중복 줄 뺌", n, "(" + ", ".join(dropped_dates) + ")")

# R5 식수 빈칸 줄 빼기
mask = df["식수"].eq("")
df = df[~mask]
record("R5", "식수 빈칸 줄 뺌", int(mask.sum()))

# R10 출근예정 빈칸 → 같은 요일 바로 앞 기록 4개(출근예정 있는 줄)의 median, 반올림(.5는 올림)
df = df.sort_values("날짜").reset_index(drop=True)
filled = []
for i in df.index[df["출근예정"].eq("")]:
    prev = df[(df.index < i) & (df["요일"] == df.at[i, "요일"]) & df["출근예정"].ne("")]
    vals = prev["출근예정"].astype(int).tail(4)
    if len(vals) < 4:
        raise ValueError(f"{df.at[i, '날짜']}: 앞 기록이 {len(vals)}개뿐 — 확인 필요")
    med = vals.median()
    val = math.floor(med + 0.5)
    df.at[i, "출근예정"] = str(val)
    filled.append(f"{df.at[i, '날짜']}({df.at[i, '요일']}) ← median({', '.join(map(str, vals))}) = {med:g} → {val}")
record("R10", "출근예정 빈칸 채움", len(filled), "; ".join(filled))

# R6 불가능한 식수 줄 빼기 · '수기 집계' 줄은 수강생 결정대로
att, meal = df["출근예정"].astype(int), df["식수"].astype(int)
manual = df["비고"].eq("수기 집계")
if MANUAL_DECISION == "×10 보정":
    df.loc[manual, "식수"] = (meal[manual] * 10).astype(str)
    meal = df["식수"].astype(int)
bad = (meal > att) | (meal < att * 0.2)
if MANUAL_DECISION == "뺀다":
    bad = bad | manual
gone = [f"{r.날짜} 출근예정 {r.출근예정} · 식수 {r.식수}" + (f" · 비고 {r.비고}" if r.비고 else "")
        for r in df[bad].itertuples()]
df = df[~bad]
record("R6", "불가능한 식수 줄 뺌", int(bad.sum()),
       f"(수기 집계 결정: {MANUAL_DECISION} · {int(manual.sum())}줄) " + "; ".join(gone))

# R7 날씨 넷으로(+ 빈칸 → 모름)
new = df["날씨"].str.strip().map(lambda s: WEATHER_MAP.get(s, s))
n = int((new != df["날씨"]).sum())
df["날씨"] = new
left = sorted(set(df["날씨"]) - {"맑음", "흐림", "비", "눈", "모름"})
if left:
    raise ValueError(f"R7 표에 없는 날씨: {left} — 확인 필요")
record("R7", "날씨 표기 고침", n)

# R8 최고기온 단위 · 공백 떼기
new = df["최고기온"].str.replace(r"℃|°C|\s", "", regex=True)
n = int((new != df["최고기온"]).sum())
df["최고기온"] = new
pd.to_numeric(df["최고기온"].replace("", None), errors="raise")  # 숫자만 남았는지 확인
record("R8", "최고기온 단위 뗌", n)

# R9 메뉴 · 행사 이름 통일 — 따로 세어 더한다
n_menu = int(df["메인메뉴"].isin(MENU_MAP).sum())
n_event = int(df["행사"].isin(EVENT_MAP).sum())
df["메인메뉴"] = df["메인메뉴"].replace(MENU_MAP)
df["행사"] = df["행사"].replace(EVENT_MAP)
record("R9", "이름 통일", n_menu + n_event, f"(메뉴 {n_menu} + 행사 {n_event})")

# 마지막 정리: 월급날 Y→1 · 빈칸→0, 출근예정 · 식수 정수, 날짜순, 원본과 같은 10개 열
df["월급날"] = df["월급날"].map({"Y": 1, "": 0})
df["출근예정"] = df["출근예정"].astype(int)
df["식수"] = df["식수"].astype(int)
df = df.sort_values("날짜")[COLS]
assert df["월급날"].notna().all() and df["날짜"].is_unique

OUT_DIR.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

lines = ["# 한빛식당(가상) 점심 기록 정제 로그", ""]
lines += [f"- 원본 `{SRC}` → 결과 `{OUT_CSV.as_posix()}` (코드 `scripts/lunch_clean.py`, 규칙 `lunch_rules.md`)"]
lines += [f"- 처음 **{n_start}줄** → 남은 **{len(df)}줄** · 날짜 {df['날짜'].min()} ~ {df['날짜'].max()}"]
lines += [f"- '수기 집계' 줄: **{MANUAL_DECISION}**", ""]
lines += ["세는 법: 그 규칙을 적용할 때 남아 있는 줄에서 센다. R2는 실제 요일과 달랐던 줄만, R9는 메뉴와 행사를 따로 세어 더한다.", ""]
lines += ["| 순서 | 규칙 | 할 일 | 고친(뺀) 줄 수 | 남은 줄 수 | 메모 |", "|---|---|---|---|---|---|"]
lines += [f"| {k} | {r} | {w} | {c} | {left_n} | {note} |" for k, (r, w, c, left_n, note) in enumerate(log, 1)]
OUT_LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")

print(f"처음 {n_start}줄 → 남은 {len(df)}줄")
print(f"저장: {OUT_CSV} · {OUT_LOG}")
