"""3일차 실습 C: 한빛식당(가상) 밥 예보 페이지 — 깨끗한 표로 계산해 HTML 한 장을 쓴다 (손으로 고치지 않음).

실행: uv run python scripts/lunch_page.py
입력: workbench/day3/outputs/lunch_clean.csv · labs/day3/lab-c/nutritionist_memo.md (읽기만)
결과: workbench/day3/outputs/hanbit_lunch.html
근거: labs/day3/lab-c/lab_c_guide.md 「5. 감 검증」 · 「6. 페이지 규칙」 · 「7. 예보관 시험」
지금 구역: 머리 → 예보 성적표 → 영양사님 감 검증. 같은 입력이면 같은 페이지(시각 없음 · 난수 시드 고정).
"""
import html
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.linear_model import LinearRegression

sys.stdout.reconfigure(encoding="utf-8")
CLEAN = "workbench/day3/outputs/lunch_clean.csv"
MEMO = "labs/day3/lab-c/nutritionist_memo.md"
PLAN = "labs/day3/lab-c/next_week_plan.csv"
OUT = Path("workbench/day3/outputs/hanbit_lunch.html")

GAP = 2.0  # 100명당 2명 이상 차이 = '차이 있음' (사람이 정한 선)

df = pd.read_csv(CLEAN, encoding="utf-8-sig", keep_default_na=False)
df["최고기온"] = pd.to_numeric(df["최고기온"].replace("", None))
df["100명당"] = df["식수"] / df["출근예정"] * 100
PERIOD = (df["날짜"].min(), df["날짜"].max())

# 메모의 믿음 글 — 원문 그대로 (번호 → 굵은 글 · 덧붙인 말)
memo_text = Path(MEMO).read_text(encoding="utf-8")
BELIEF_TEXT = {
    int(m[1]): (m[2].strip(), m[3].strip())
    for m in re.finditer(r"^(\d)\. \*\*(.+?)\*\*(.*)$", memo_text, flags=re.M)
}


def esc(s):
    return html.escape(str(s))


def r1(x):
    return round(float(x), 1)


# ── 감 검증 계산 ─────────────────────────────────────────────
# 비교 바탕 = 행사가 없고 월급날이 아닌 날. 그룹 값 = 그날그날의 '출근 100명당 식수'의 평균.
base = df[(df["행사"] == "") & (df["월급날"] == 0)]


def group(name, rows):
    return {"name": name, "value": r1(rows["100명당"].mean()), "days": int(len(rows)), "_raw": rows["100명당"].mean()}


def judge(expected_high, expected_low):
    """믿음이 'expected_high가 expected_low보다 많다'일 때 판정."""
    diff = expected_high["_raw"] - expected_low["_raw"]
    if diff >= GAP:
        return "맞음", diff
    if diff <= -GAP:
        return "틀림", diff
    return "반만", diff


beliefs = []

# 믿음 1 비 오는 날 vs 맑은 날 — 비 오는 날이 많다
rain, sunny = group("비 오는 날", base[base["날씨"] == "비"]), group("맑은 날", base[base["날씨"] == "맑음"])
verdict, diff = judge(rain, sunny)
beliefs.append({"no": 1, "groups": [rain, sunny], "verdict": verdict, "diff": diff,
                "how": "비 오는 날이 맑은 날보다 많으면 맞음"})

# 믿음 2 금요일 vs 월–목 — 금요일이 적다
fri, mon_thu = group("금요일", base[base["요일"] == "금"]), group("월–목", base[base["요일"].isin(list("월화수목"))])
verdict, diff = judge(mon_thu, fri)
beliefs.append({"no": 2, "groups": [fri, mon_thu], "verdict": verdict, "diff": diff,
                "how": "금요일이 월–목보다 적으면 맞음"})

# 믿음 3 메뉴별(높은 순) — 돈가스가 1등이고 2등보다 2명 이상 많으면 맞음
menus = [group(m, g) for m, g in base.groupby("메인메뉴")]
menus.sort(key=lambda g: g["_raw"], reverse=True)
top, second = menus[0], menus[1]
pork = next(g for g in menus if g["name"] == "돈가스")
if top["name"] == "돈가스":
    verdict = "맞음" if top["_raw"] - second["_raw"] >= GAP else "반만"
    diff = top["_raw"] - second["_raw"]
    rival = second
else:
    verdict = "반만" if top["_raw"] - pork["_raw"] < GAP else "틀림"
    diff = pork["_raw"] - top["_raw"]
    rival = top
beliefs.append({"no": 3, "groups": [pork, rival], "verdict": verdict, "diff": diff, "menus": menus,
                "pork_rank": menus.index(pork) + 1,
                "how": "돈가스가 1등이고 2등보다 2명 이상 많으면 맞음"})

# 믿음 4 최고기온 31도 이상 vs 25도 이상 31도 미만 — 더우면 적다 (최고기온 빈칸은 뺀다)
hot = group("31도 이상", base[base["최고기온"] >= 31])
warm = group("25도 이상 31도 미만", base[(base["최고기온"] >= 25) & (base["최고기온"] < 31)])
verdict, diff = judge(warm, hot)
beliefs.append({"no": 4, "groups": [hot, warm], "verdict": verdict, "diff": diff,
                "how": "31도 이상인 날이 25–31도 날보다 적으면 맞음"})

# 믿음 5 월요일 vs 화–목 — 월요일이 적다
mon, tue_thu = group("월요일", base[base["요일"] == "월"]), group("화–목", base[base["요일"].isin(list("화수목"))])
verdict, diff = judge(tue_thu, mon)
beliefs.append({"no": 5, "groups": [mon, tue_thu], "verdict": verdict, "diff": diff,
                "how": "월요일이 화–목보다 적으면 맞음"})

# 메모에 없던 규칙: 월급날(월급날인 날 모두) vs 보통 날(행사 없고 월급날 아닌 날)
payday, normal = group("월급날", df[df["월급날"] == 1]), group("보통 날", base)
pay_diff = payday["_raw"] - normal["_raw"]
pay_text = ("차이 있음 — 월급날이 더 많음" if pay_diff >= GAP
            else "차이 있음 — 월급날이 더 적음" if pay_diff <= -GAP else "차이 작음(2명 안쪽)")

# ── 예보관 시험 계산 ─────────────────────────────────────────
TEST_START = "2026-09-14"  # 이 날 전 = 배우는 기간, 이 날부터 = 시험 기간
TEXT_COLS = ["요일", "날씨", "메인메뉴", "행사"]
NUM_COLS = ["최고기온", "월급날", "출근예정"]
MENU_FACTOR = {"돈가스": 1.1, "카레": 1.1, "샐러드": 0.9}  # 나머지 1.0
EXTRA = 10  # AI 준비 = 예보 + 10
COST = 4500  # 1인분 원가(가정)


def round_half_up(x):
    return int(math.floor(x + 0.5))


def md(day):
    m, d = day[5:7], day[8:10]
    return f"{int(m)}/{int(d)}"


train = df[df["날짜"] < TEST_START].copy()
test = df[df["날짜"] >= TEST_START].copy()
TEMP_FILL = float(train["최고기온"].median())  # 최고기온 빈칸 = 배우는 기간의 가운데 값


def features(rows, columns=None):
    x = rows[TEXT_COLS + NUM_COLS].copy()
    x["행사"] = x["행사"].replace("", "없음")
    x["최고기온"] = x["최고기온"].fillna(TEMP_FILL)
    x = pd.get_dummies(x, columns=TEXT_COLS, dtype=float)  # drop_first 없이
    if columns is not None:  # 배울 때와 같은 열 · 없는 열은 0
        x = x.reindex(columns=columns, fill_value=0.0)
    return x.astype(float)


X_train = features(train)
FEATURE_COLS = list(X_train.columns)
X_test = features(test, FEATURE_COLS)
y_train, y_test = train["식수"].astype(float), test["식수"].astype(float)

forecasters = {
    "선형 회귀": LinearRegression(),
    "LightGBM": LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=15,
                              min_child_samples=5, random_state=42, verbose=-1),
}
test_pred, score = {}, {}
for name, model in forecasters.items():
    model.fit(X_train.to_numpy(), y_train.to_numpy())
    test_pred[name] = model.predict(X_test.to_numpy())
    score[name] = float((abs(test_pred[name] - y_test.to_numpy())).mean())  # 하루 평균 몇 인분 차이
OUR = min(score, key=score.get)
OTHER = next(n for n in score if n != OUR)
OUR_MODEL = forecasters[OUR]


def nutritionist_formula(day, weekday, menu):
    """그날 전 같은 요일의 실제 식수 4개(깨끗한 표에서 가장 가까운 날부터) 평균 × 메뉴 배수."""
    prev = df[(df["날짜"] < day) & (df["요일"] == weekday)].sort_values("날짜").tail(4)
    if len(prev) < 4:
        raise ValueError(f"{day}: 같은 요일 앞 기록 {len(prev)}개 — 확인 필요")
    return prev["식수"].mean() * MENU_FACTOR.get(menu, 1.0), list(prev["날짜"])


test = test.reset_index(drop=True)
test["AI 예보"] = [round_half_up(p) for p in test_pred[OUR]]
test["AI 준비"] = test["AI 예보"] + EXTRA
test["공식 원값"] = [nutritionist_formula(r.날짜, r.요일, r.메인메뉴)[0] for r in test.itertuples()]
test["공식 준비"] = test["공식 원값"].map(round_half_up)


def outcome(prep):
    left = (prep - test["식수"]).clip(lower=0)
    short = (test["식수"] - prep).clip(lower=0)
    return {"left": int(left.sum()), "left_won": int(left.sum()) * COST,
            "short": int(short.sum()), "short_days": int((short > 0).sum())}


ai_out, formula_out = outcome(test["AI 준비"]), outcome(test["공식 준비"])
ai_mae = score[OUR]
formula_mae = float((test["공식 준비"] - test["식수"]).abs().mean())
EVENT_DAYS = {"2026-09-23": "추석 연휴 전날 · 돈가스", "2026-09-30": "비 오는 수요일 · 카레"}

# ── 다음 주 예보 계산 ─────────────────────────────────────────
# 우리 예보관(시험에서 이긴 모델, 배우는 기간으로 배운 그대로)에게 묻는다.
nxt = pd.read_csv(PLAN, encoding="utf-8-sig", keep_default_na=False)
nxt = nxt.rename(columns={"날씨예보": "날씨", "최고기온예보": "최고기온"})
nxt["최고기온"] = pd.to_numeric(nxt["최고기온"].replace("", None))
nxt["월급날"] = nxt["월급날"].map(lambda v: 1 if v == "Y" else 0)
nxt["출근예정"] = nxt["출근예정"].astype(int)
nxt["예보"] = [round_half_up(p) for p in OUR_MODEL.predict(features(nxt, FEATURE_COLS).to_numpy())]
nxt["준비"] = nxt["예보"] + EXTRA
nxt["공식 원값"] = [nutritionist_formula(r["날짜"], r["요일"], r["메인메뉴"])[0] for _, r in nxt.iterrows()]
nxt["공식"] = nxt["공식 원값"].map(round_half_up)
MAX_DAY = nxt.loc[nxt["예보"].idxmax(), "날짜"]
MIN_DAY = nxt.loc[nxt["예보"].idxmin(), "날짜"]

# 코멘트의 근거로 쓸 감 검증 숫자(출근 100명당) — 위에서 계산한 값만 끼워 넣는다
EVIDENCE = {
    "비": f"기록에서 비 오는 날은 100명당 {rain['value']:.1f}명(맑은 날 {sunny['value']:.1f}명)",
    "금": f"기록에서 금요일은 100명당 {fri['value']:.1f}명(월–목 {mon_thu['value']:.1f}명)",
    "월급날": f"기록에서 월급날은 100명당 {payday['value']:.1f}명(보통 날 {normal['value']:.1f}명)",
}
MENU_RANK = {g["name"]: (i + 1, g["value"]) for i, g in enumerate(menus)}

# ── '만약에' 시뮬레이터 계산 ──────────────────────────────────
# 우리 예보관이 선형 회귀이면 그 모델, LightGBM이면 이 구역만 선형 회귀(같은 배우는 기간)로 계산한다.
SIM_MODEL = OUR_MODEL if OUR == "선형 회귀" else forecasters["선형 회귀"]
SIM = {
    "intercept": float(SIM_MODEL.intercept_),
    "coef": {c: float(w) for c, w in zip(FEATURE_COLS, SIM_MODEL.coef_)},  # 배울 때 만든 열 이름 그대로
    "tempFill": TEMP_FILL,
    "options": {
        "요일": list("월화수목금"),
        "날씨": ["맑음", "흐림", "비", "눈"],
        "메인메뉴": sorted(df["메인메뉴"].unique()),
        "행사": ["없음"] + sorted(v for v in df["행사"].unique() if v),
    },
    "base": {"요일": "화", "날씨": "맑음", "최고기온": 22, "메인메뉴": "비빔밥", "행사": "없음", "월급날": 0, "출근예정": 470},
    "presets": [{"label": f"{md(r['날짜'])}({r['요일']})", "요일": r["요일"], "날씨": r["날씨"],
                 "최고기온": float(r["최고기온"]), "메인메뉴": r["메인메뉴"], "행사": r["행사"] or "없음",
                 "월급날": int(r["월급날"]), "출근예정": int(r["출근예정"])} for _, r in nxt.iterrows()],
    "extra": EXTRA,
    "fallbackNote": "" if OUR == "선형 회귀" else "우리 예보관은 LightGBM이지만, 이 구역만 선형 회귀로 계산합니다.",
}


def sim_predict(day):
    """페이지 JavaScript와 같은 식 · 같은 순서: 절편 + Σ(계수 × 값)."""
    total = SIM["intercept"]
    for col, w in SIM["coef"].items():
        if col in NUM_COLS:
            v = day[col]
            if col == "최고기온" and (v is None or v == ""):
                v = SIM["tempFill"]
            total += w * float(v)
        else:
            group_name, value = col.split("_", 1)
            total += w * (1.0 if day[group_name] == value else 0.0)
    return total


SIM_BASE = round_half_up(sim_predict(SIM["base"]))
SIM_CHECK = [(p["label"], round_half_up(sim_predict(p))) for p in SIM["presets"]]
if OUR == "선형 회귀":  # 스스로 확인: 불러온 하루의 예보 = '다음 주 예보' 카드 숫자
    for (label, v), card in zip(SIM_CHECK, nxt["예보"]):
        assert v == card, f"만약에 {label}: {v} ≠ 카드 {card}"


def topic(word):
    """받침이 있으면 '은', 없으면 '는'."""
    last = word[-1]
    has_final = "가" <= last <= "힣" and (ord(last) - ord("가")) % 28 != 0
    return word + ("은" if has_final else "는")


def comment(r):
    cond = [f"{r['요일']}요일", r["날씨"], r["메인메뉴"]]
    if r["행사"]:
        cond.append(r["행사"])
    if r["월급날"]:
        cond.append("월급날")
    gap = r["준비"] - r["공식"]
    if gap == 0:
        vs = f"영양사님 공식({r['공식']}인분)과 같아요"
    else:
        vs = f"영양사님 공식({r['공식']}인분)보다 {abs(gap)}인분 {'많아요' if gap > 0 else '적어요'}"
    if r["월급날"]:
        why = EVIDENCE["월급날"]
    elif r["날씨"] == "비":
        why = EVIDENCE["비"]
    elif r["요일"] == "금":
        why = EVIDENCE["금"]
    elif r["메인메뉴"] in MENU_RANK:
        rank, val = MENU_RANK[r["메인메뉴"]]
        why = f"기록에서 {topic(r['메인메뉴'])} 메뉴 {len(menus)}개 중 {rank}등(100명당 {val:.1f}명)"
    else:
        why = ""
    tail = f" — {why}이에요." if why else "."
    return f"영양사님, {' · '.join(cond)}인 날이에요. 준비 {r['준비']}인분은 {vs}{tail}"

# ── HTML ────────────────────────────────────────────────────
BADGE_CLASS = {"맞음": "ok", "반만": "half", "틀림": "bad"}
charts = {}  # canvas id → 막대 데이터 (페이지 안 JSON)


def two_numbers(groups):
    cells = "".join(
        f'<div class="num"><span class="lab">{esc(g["name"])}</span>'
        f'<b>{g["value"]:.1f}</b><span class="unit">명</span>'
        f'<span class="days">{g["days"]}일</span></div>' for g in groups)
    return f'<div class="nums">{cells}</div>'


def belief_card(b):
    no = b["no"]
    head, tail = BELIEF_TEXT[no]
    cid = f"belief{no}"
    if no == 3:
        rows = b["menus"]
        charts[cid] = {"labels": [g["name"] for g in rows], "values": [g["value"] for g in rows],
                       "hi": [g["name"] == "돈가스" for g in rows], "horizontal": True}
        extra = (f'<p class="note">돈가스는 메뉴 {len(rows)}개 중 {b["pork_rank"]}등 · '
                 f'1등 {esc(rows[0]["name"])} {rows[0]["value"]:.1f}명</p>')
        height = 26 * len(rows) + 30
    else:
        rows = b["groups"]
        charts[cid] = {"labels": [g["name"] for g in rows], "values": [g["value"] for g in rows],
                       "hi": [True, False], "horizontal": True}
        extra = ""
        if no == 4:
            extra = f'<p class="note">31도 이상인 날: {b["groups"][0]["days"]}일</p>'
        height = 110
    sign = "+" if b["diff"] >= 0 else "−"
    return f"""
<article class="card">
  <div class="card-top"><span class="no">믿음 {no}</span>
    <span class="badge {BADGE_CLASS[b["verdict"]]}">{b["verdict"]}</span></div>
  <h3>{esc(head)}</h3>
  <p class="quote">{esc(tail)}</p>
  {two_numbers(b["groups"])}
  <div class="chart" style="height:{height}px"><canvas id="{cid}" aria-label="믿음 {no} 막대 그래프"></canvas></div>
  {extra}
  <p class="how">판정 기준: {esc(b["how"])} · 믿음 방향 차이 {sign}{abs(b["diff"]):.1f}명</p>
</article>"""


def payday_card():
    cid = "payday"
    charts[cid] = {"labels": [payday["name"], normal["name"]], "values": [payday["value"], normal["value"]],
                   "hi": [True, False], "horizontal": True}
    sign = "+" if pay_diff >= 0 else "−"
    return f"""
<article class="card extra-rule">
  <div class="card-top"><span class="no">메모에 없던 규칙</span>
    <span class="badge half">메모에 없음</span></div>
  <h3>월급날에는 식수가 달라질까?</h3>
  <p class="quote">월급날인 날 모두와 보통 날(행사 없고 월급날 아닌 날)을 견줬습니다.</p>
  {two_numbers([payday, normal])}
  <div class="chart" style="height:110px"><canvas id="{cid}" aria-label="월급날 막대 그래프"></canvas></div>
  <p class="how">{esc(pay_text)} · 월급날 − 보통 날 {sign}{abs(pay_diff):.1f}명</p>
</article>"""


def section_head():
    return f"""
<header class="head">
  <h1>한빛식당 밥 예보</h1>
  <p>(가상) 한빛정밀(주) 본사 구내식당 · 기록 기간 {PERIOD[0]} ~ {PERIOD[1]} · 만든 사람 총무팀 최 대리(가상)</p>
</header>"""


LINE = {}  # 시험 20일 선 그래프 데이터 (페이지 안 JSON)


def section_next_week():
    cards = ""
    for _, r in nxt.iterrows():
        flag = ""
        if r["날짜"] == MAX_DAY:
            flag = '<span class="flag hi">이번 주 가장 많은 날</span>'
        elif r["날짜"] == MIN_DAY:
            flag = '<span class="flag lo">이번 주 가장 적은 날</span>'
        chips = [r["날씨"], r["메인메뉴"]] + ([r["행사"]] if r["행사"] else []) + (["월급날"] if r["월급날"] else [])
        chip_html = "".join(f'<span class="chip">{esc(c)}</span>' for c in chips)
        cards += f"""
    <article class="day{' is-max' if r['날짜'] == MAX_DAY else ''}{' is-min' if r['날짜'] == MIN_DAY else ''}">
      <div class="day-top"><span class="date">{md(r['날짜'])}</span><span class="wd">{r['요일']}요일</span></div>
      {flag}
      <p class="big"><b>{r['예보']}</b>명</p>
      <p class="prep">준비 {r['준비']}인분</p>
      <p class="formula">영양사님 공식이면 {r['공식']}인분</p>
      <div class="chips">{chip_html}</div>
      <p class="comment">{esc(comment(r))}</p>
    </article>"""
    return f"""
<section id="next-week">
  <h2>다음 주 예보</h2>
  <p class="lead">{nxt['날짜'].min()} ~ {nxt['날짜'].max()} · 시험에서 이긴 우리 예보관({esc(OUR)})이 계획표(메뉴 · 날씨예보 · 행사 · 출근예정)를 보고 예보했습니다.
    준비 인분 = 예보 + {EXTRA}. 준비량은 영양사님이 정해 주세요.</p>
  <div class="week">{cards}
  </div>
</section>"""


def section_whatif():
    def select(name, label):
        opts = "".join(f'<option value="{esc(v)}">{esc(v)}</option>' for v in SIM["options"][name])
        return f'<label class="field"><span>{label}</span><select data-k="{esc(name)}">{opts}</select></label>'

    presets = "".join(f'<button type="button" class="preset" data-i="{i}">{esc(p["label"])}</button>'
                      for i, p in enumerate(SIM["presets"]))
    note = f'<p class="note">{esc(SIM["fallbackNote"])}</p>' if SIM["fallbackNote"] else ""
    return f"""
<section id="whatif">
  <h2>만약에 — 조건을 골라 보기</h2>
  <p class="lead">조건을 바꾸면 우리 예보관({esc(OUR)})의 계산식으로 예보가 바로 다시 나옵니다.
    처음 값은 기준 하루(화요일 · 맑음 · 22도 · 비빔밥 · 행사 없음 · 월급날 아님 · 출근 470명)입니다.</p>{note}
  <div class="card sim">
    <div class="presets"><span class="lab">다음 주 하루 불러오기</span>{presets}
      <button type="button" class="preset reset" data-i="base">기준 하루</button></div>
    <div class="fields">
      {select("요일", "요일")}{select("날씨", "날씨")}{select("메인메뉴", "메인메뉴")}{select("행사", "행사")}
      <label class="field"><span>월급날</span><select data-k="월급날"><option value="0">아님</option><option value="1">맞음</option></select></label>
      <label class="field"><span>출근 인원(명)</span><input type="number" inputmode="numeric" min="0" step="1" data-k="출근예정"></label>
      <label class="field"><span>최고기온(도)</span><input type="number" inputmode="decimal" step="0.1" data-k="최고기온"></label>
    </div>
    <div class="sim-out" aria-live="polite">
      <p class="big"><b id="sim-n">{SIM_BASE}</b>명 · 준비 <b id="sim-prep">{SIM_BASE + EXTRA}</b>인분</p>
      <p id="sim-vs" class="formula">기준 하루와 같음</p>
    </div>
  </div>
</section>"""


def section_scorecard():
    LINE.update({
        "labels": [f"{md(r.날짜)}({r.요일})" for r in test.itertuples()],
        "actual": [int(v) for v in test["식수"]],
        "ai": [int(v) for v in test["AI 예보"]],
        "formula": [int(v) for v in test["공식 준비"]],
        "marks": [i for i, d in enumerate(test["날짜"]) if d in EVENT_DAYS],
        "ourName": OUR,
    })
    rows = "".join(
        f'<div class="fc{" pick" if n == OUR else ""}"><span class="lab">{esc(n)}</span>'
        f'<b>{score[n]:.1f}</b><span class="unit">인분 차이 / 하루</span>'
        f'{"<span class=pick-tag>우리 예보관</span>" if n == OUR else ""}</div>' for n in forecasters)
    notes = ""
    for _, r in test[test["날짜"].isin(EVENT_DAYS)].iterrows():
        notes += (f'<li><b>{md(r["날짜"])}({r["요일"]}) {esc(EVENT_DAYS[r["날짜"]])}</b> — 실제 {r["식수"]}명 · '
                  f'AI 예보 {r["AI 예보"]}명(준비 {r["AI 준비"]}인분) · 영양사님 공식 {r["공식 준비"]}인분</li>')

    def compare(title, ai_val, f_val, ai_sub="", f_sub="", note=""):
        return f"""
    <article class="card cmp">
      <h3>{title}</h3>
      <div class="nums">
        <div class="num"><span class="lab">AI(우리 예보관 + {EXTRA})</span><b>{ai_val}</b><span class="days">{ai_sub}</span></div>
        <div class="num"><span class="lab">영양사님 공식</span><b>{f_val}</b><span class="days">{f_sub}</span></div>
      </div>{note}
    </article>"""

    cards = (
        compare("하루 평균 몇 인분 차이", f"{ai_mae:.1f}", f"{formula_mae:.1f}", "인분", "인분",
                '<p class="how">AI는 예보, 공식은 준비량과 실제의 차이(크기만)를 평균</p>')
        + compare("남은 밥", f'{ai_out["left"]:,}', f'{formula_out["left"]:,}',
                  f'인분 · {ai_out["left_won"]:,}원', f'인분 · {formula_out["left_won"]:,}원',
                  f'<p class="how">1인분 원가 {COST:,}원(가정) · 시험 {len(test)}일 합계</p>')
        + compare("모자란 밥 (= 컵라면을 드신 분)", f'{ai_out["short"]:,}', f'{formula_out["short"]:,}',
                  f'인분 · {ai_out["short_days"]}일', f'인분 · {formula_out["short_days"]}일',
                  '<p class="how">인분 합계 · 모자란 날 수</p>')
    )
    return f"""
<section id="scorecard">
  <h2>예보 성적표</h2>
  <p class="lead">{train["날짜"].min()} ~ {train["날짜"].max()}({len(train)}일)로 배우고,
    배울 때 쓰지 않은 최근 {len(test)}일({test["날짜"].min()} ~ {test["날짜"].max()})로 시험했습니다.</p>
  <div class="forecasters">{rows}</div>
  <p class="tally">복잡한 쪽이 늘 이기지는 않는다 — 시험으로 고른다</p>
  <p class="note">예보관 설정은 모두 같은 결과를 보려고 고정</p>
  <article class="card wide">
    <h3>시험 {len(test)}일 — 실제 · 우리 예보관({esc(OUR)}) · 영양사님 공식</h3>
    <div class="chart" style="height:300px"><canvas id="testline" aria-label="시험 기간 선 그래프"></canvas></div>
    <ul class="marks">{notes}</ul>
  </article>
  <div class="cards three">{cards}
  </div>
</section>"""


def section_beliefs():
    cards = "".join(belief_card(b) for b in beliefs) + payday_card()
    tally = {v: sum(b["verdict"] == v for b in beliefs) for v in ["맞음", "반만", "틀림"]}
    return f"""
<section id="beliefs">
  <h2>영양사님 감 검증</h2>
  <p class="lead">정 영양사님(가상)의 믿음 다섯 가지를 기록으로 확인했습니다.
    출근 인원이 다른 날도 견줄 수 있게 <b>출근 100명당 식수</b>(식수 ÷ 출근예정 × 100, 날마다 구해 평균)로 비교하고,
    행사가 없고 월급날이 아닌 날 {len(base)}일만 썼습니다. 100명당 2명 이상 차이 나면 '차이 있음'으로 봅니다.</p>
  <p class="tally">맞음 {tally["맞음"]} · 반만 {tally["반만"]} · 틀림 {tally["틀림"]}</p>
  <div class="cards">{cards}
  </div>
</section>"""


CSS = """
:root { --bg:#f4f5f7; --card:#ffffff; --ink:#1d2330; --sub:#5b6474; --line:#e3e6eb;
        --accent:#1f6feb; --warn:#d1495b; --gray:#8a93a3; }
* { box-sizing:border-box; }
html { -webkit-text-size-adjust:100%; }
body { margin:0; background:var(--bg); color:var(--ink); font-family:'Noto Sans KR', sans-serif;
       font-size:16px; line-height:1.6; word-break:keep-all; overflow-wrap:break-word; }
main { max-width:1080px; margin:0 auto; padding:24px 16px 48px; }
.head { padding:8px 0 20px; border-bottom:1px solid var(--line); margin-bottom:24px; }
.head h1 { margin:0 0 4px; font-size:28px; font-weight:700; }
.head p { margin:0; color:var(--sub); font-size:15px; }
section h2 { font-size:22px; margin:0 0 8px; }
.lead { color:var(--sub); margin:0 0 8px; font-size:15px; }
.tally { margin:0 0 16px; font-weight:700; }
.cards { display:grid; grid-template-columns:repeat(auto-fill, minmax(min(100%, 320px), 1fr)); gap:16px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:16px; min-width:0; }
.card.extra-rule { border-style:dashed; }
.card-top { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.no { color:var(--sub); font-size:14px; font-weight:700; }
.badge { font-size:14px; font-weight:700; padding:2px 10px; border-radius:999px; color:#fff; white-space:nowrap; }
.badge.ok { background:var(--accent); } .badge.half { background:var(--gray); } .badge.bad { background:var(--warn); }
.card h3 { font-size:18px; margin:8px 0 2px; }
.quote { color:var(--sub); font-size:14px; margin:0 0 12px; }
.nums { display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:8px; }
.num { background:var(--bg); border-radius:8px; padding:8px 10px; display:flex; flex-wrap:wrap; align-items:baseline; gap:2px 4px; }
.num .lab { width:100%; font-size:14px; color:var(--sub); }
.num b { font-size:24px; } .num .unit { font-size:14px; } .num .days { margin-left:auto; font-size:14px; color:var(--sub); }
.chart { position:relative; width:100%; }
section + section { margin-top:40px; }
.forecasters { display:grid; grid-template-columns:repeat(auto-fit, minmax(min(100%, 240px), 1fr)); gap:12px; margin-bottom:12px; }
.fc { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px 14px;
      display:flex; flex-wrap:wrap; align-items:baseline; gap:2px 6px; }
.fc .lab { width:100%; font-size:14px; color:var(--sub); font-weight:700; }
.fc b { font-size:28px; } .fc .unit { font-size:14px; color:var(--sub); }
.fc.pick { border:2px solid var(--accent); }
.pick-tag { margin-left:auto; font-size:14px; font-weight:700; color:var(--accent); }
.card.wide { margin:16px 0; }
.marks { margin:12px 0 0; padding-left:18px; font-size:14px; }
.marks li + li { margin-top:4px; }
.cards.three { grid-template-columns:repeat(auto-fit, minmax(min(100%, 280px), 1fr)); }
.week { display:grid; grid-template-columns:1fr; gap:12px; }
@media (min-width:900px) { .week { grid-template-columns:repeat(5, minmax(0, 1fr)); } }
.day { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px; min-width:0;
       display:flex; flex-direction:column; gap:4px; }
.day.is-max { border:2px solid var(--accent); } .day.is-min { border:2px solid var(--warn); }
.day-top { display:flex; justify-content:space-between; align-items:baseline; }
.date { font-size:20px; font-weight:700; } .wd { color:var(--sub); font-size:15px; }
.flag { align-self:flex-start; font-size:14px; font-weight:700; padding:1px 8px; border-radius:999px; color:#fff; }
.flag.hi { background:var(--accent); } .flag.lo { background:var(--warn); }
.big { margin:4px 0 0; font-size:16px; } .big b { font-size:40px; line-height:1.1; }
.prep { margin:0; font-size:17px; font-weight:700; }
.formula { margin:0; font-size:14px; color:var(--sub); }
.chips { display:flex; flex-wrap:wrap; gap:4px; margin:6px 0; }
.chip { font-size:14px; padding:1px 8px; border-radius:6px; background:var(--bg); border:1px solid var(--line); }
.comment { margin:0; font-size:14px; color:var(--ink); }
.sim { display:flex; flex-direction:column; gap:14px; }
.presets { display:flex; flex-wrap:wrap; gap:6px; align-items:center; }
.presets .lab { width:100%; font-size:14px; color:var(--sub); font-weight:700; }
.preset { font:inherit; font-size:15px; padding:6px 12px; border-radius:8px; border:1px solid var(--line);
          background:var(--bg); color:var(--ink); cursor:pointer; }
.preset:hover, .preset:focus-visible { border-color:var(--accent); outline:none; }
.preset.reset { color:var(--sub); }
.fields { display:grid; grid-template-columns:repeat(auto-fill, minmax(min(100%, 150px), 1fr)); gap:10px; }
.field { display:flex; flex-direction:column; gap:2px; min-width:0; }
.field span { font-size:14px; color:var(--sub); }
.field select, .field input { font:inherit; font-size:16px; width:100%; padding:8px; border-radius:8px;
          border:1px solid var(--line); background:var(--card); color:var(--ink); }
.sim-out { border-top:1px solid var(--line); padding-top:10px; }
.sim-out .big b { color:var(--accent); }
.note, .how { font-size:14px; color:var(--sub); margin:8px 0 0; }
"""

JS = """
const DATA = JSON.parse(document.getElementById('page-data').textContent);
const css = getComputedStyle(document.documentElement);
const ACCENT = css.getPropertyValue('--accent').trim(), GRAY = '#c3c9d3';
Chart.defaults.font.family = "'Noto Sans KR', sans-serif";
Chart.defaults.font.size = 14;
for (const [id, c] of Object.entries(DATA.charts)) {
  new Chart(document.getElementById(id), {
    type: 'bar',
    data: { labels: c.labels, datasets: [{ data: c.values, backgroundColor: c.hi.map(h => h ? ACCENT : GRAY),
            borderRadius: 4, barThickness: 16 }] },
    options: { indexAxis: c.horizontal ? 'y' : 'x', responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { display: false },
                 tooltip: { callbacks: { label: ctx => ctx.parsed.x.toFixed(1) + '명 (100명당)' } } },
      scales: { x: { beginAtZero: true, suggestedMax: 100, grid: { color: '#eef0f3' } }, y: { grid: { display: false } } } }
  });
}
const S = DATA.sim;
if (S) {
  const NUM = ['최고기온', '월급날', '출근예정'];
  const roundHalfUp = x => Math.floor(x + 0.5);
  const predict = day => {  // 절편 + Σ(계수 × 값) — 스크립트의 sim_predict와 같은 순서
    let total = S.intercept;
    for (const [col, w] of Object.entries(S.coef)) {
      if (NUM.includes(col)) {
        let v = day[col];
        if (col === '최고기온' && (v === '' || v === null || Number.isNaN(v))) v = S.tempFill;
        total += w * Number(v);
      } else {
        const cut = col.indexOf('_');
        total += w * (day[col.slice(0, cut)] === col.slice(cut + 1) ? 1 : 0);
      }
    }
    return total;
  };
  const baseN = roundHalfUp(predict(S.base));
  const box = document.getElementById('whatif');
  const inputs = [...box.querySelectorAll('[data-k]')];
  const read = () => {
    const day = {};
    for (const el of inputs) {
      const k = el.dataset.k;
      if (k === '월급날') day[k] = Number(el.value);
      else if (k === '출근예정') day[k] = el.value === '' ? 0 : Number(el.value);
      else if (k === '최고기온') day[k] = el.value === '' ? '' : Number(el.value);
      else day[k] = el.value;
    }
    return day;
  };
  const show = () => {
    const n = roundHalfUp(predict(read())), gap = n - baseN;
    document.getElementById('sim-n').textContent = n;
    document.getElementById('sim-prep').textContent = n + S.extra;
    document.getElementById('sim-vs').textContent =
      gap === 0 ? '기준 하루와 같음' : '기준 하루보다 ' + Math.abs(gap) + '명 ' + (gap > 0 ? '많음' : '적음');
  };
  const fill = day => {
    for (const el of inputs) el.value = String(day[el.dataset.k]);
    show();
  };
  for (const el of inputs) { el.addEventListener('input', show); el.addEventListener('change', show); }
  for (const b of box.querySelectorAll('.preset'))
    b.addEventListener('click', () => fill(b.dataset.i === 'base' ? S.base : S.presets[Number(b.dataset.i)]));
  fill(S.base);
}
const L = DATA.line;
if (L && L.labels) {
  const WARN = css.getPropertyValue('--warn').trim(), INK = css.getPropertyValue('--ink').trim();
  const mark = (base, big) => L.labels.map((_, i) => L.marks.includes(i) ? big : base);
  new Chart(document.getElementById('testline'), {
    type: 'line',
    data: { labels: L.labels, datasets: [
      { label: '실제', data: L.actual, borderColor: INK, backgroundColor: INK, borderWidth: 2,
        pointRadius: mark(2, 7), pointBackgroundColor: mark(INK, WARN), pointBorderColor: mark(INK, WARN) },
      { label: '우리 예보관(' + L.ourName + ')', data: L.ai, borderColor: ACCENT, backgroundColor: ACCENT,
        borderWidth: 2, pointRadius: 2 },
      { label: '영양사님 공식', data: L.formula, borderColor: '#8a93a3', backgroundColor: '#8a93a3',
        borderWidth: 2, borderDash: [6, 4], pointRadius: 2 } ] },
    options: { responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: 'index', intersect: false },
      plugins: { legend: { position: 'bottom', labels: { boxWidth: 14 } },
                 tooltip: { callbacks: { label: ctx => ctx.dataset.label + ' ' + ctx.parsed.y + '명' } } },
      scales: { x: { ticks: { maxRotation: 60, autoSkip: true } }, y: { grid: { color: '#eef0f3' } } } }
  });
}
"""


def page(body):
    data = json.dumps({"charts": charts, "line": LINE, "sim": SIM}, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>한빛식당 밥 예보</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>{CSS}</style>
</head>
<body>
<main>{body}
</main>
<script type="application/json" id="page-data">{data}</script>
<script>{JS}</script>
</body>
</html>
"""


# 구역 순서: 머리 → 다음 주 예보 → 만약에 → 예보 성적표 → 영양사님 감 검증
sections = [section_head(), section_next_week(), section_whatif(), section_scorecard(), section_beliefs()]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(page("".join(sections)), encoding="utf-8")

print(f"기록 기간 {PERIOD[0]} ~ {PERIOD[1]} · 깨끗한 표 {len(df)}일 · 비교 바탕(행사 없고 월급날 아님) {len(base)}일")
for b in beliefs:
    nums = " vs ".join(f"{g['name']} {g['value']:.1f}({g['days']}일)" for g in b["groups"])
    print(f"믿음 {b['no']}: {nums} · 믿음 방향 차이 {b['diff']:+.2f} → {b['verdict']}")
print("  메뉴 순위: " + " > ".join(f"{g['name']} {g['value']:.1f}({g['days']}일)" for g in menus))
print(f"월급날: {payday['name']} {payday['value']:.1f}({payday['days']}일) vs {normal['name']} {normal['value']:.1f}"
      f"({normal['days']}일) · 차이 {pay_diff:+.2f} → {pay_text}")
print(f"\n[예보관 시험] 배우는 기간 {len(train)}일 · 시험 기간 {len(test)}일 · 최고기온 빈칸 채움 {TEMP_FILL:g}")
for n in forecasters:
    print(f"  {n}: 하루 평균 {score[n]:.2f}인분 차이" + ("  ← 우리 예보관" if n == OUR else ""))
print(f"  영양사님 공식: 하루 평균 {formula_mae:.2f}인분 차이")
for d in EVENT_DAYS:
    r = test[test["날짜"] == d].iloc[0]
    print(f"  {d}: 실제 {r['식수']} · AI 예보 {r['AI 예보']}(준비 {r['AI 준비']}) · 공식 {r['공식 준비']}"
          f"({r['공식 원값']:.2f})")
print(f"  남은 밥 AI {ai_out['left']}인분({ai_out['left_won']:,}원) · 공식 {formula_out['left']}인분({formula_out['left_won']:,}원)")
print(f"  모자란 밥 AI {ai_out['short']}인분 {ai_out['short_days']}일 · 공식 {formula_out['short']}인분 {formula_out['short_days']}일")
print(f"\n[다음 주 예보] 우리 예보관 {OUR}")
for _, r in nxt.iterrows():
    mark = " ← 가장 많은 날" if r["날짜"] == MAX_DAY else " ← 가장 적은 날" if r["날짜"] == MIN_DAY else ""
    print(f"  {r['날짜']}({r['요일']}) {r['메인메뉴']}: 예보 {r['예보']} · 준비 {r['준비']} · 공식 {r['공식']}"
          f"({r['공식 원값']:.2f}){mark}")
    print(f"    {comment(r)}")
print(f"\n[만약에] 계산 모델 {'선형 회귀(우리 예보관)' if OUR == '선형 회귀' else '선형 회귀(대신)'} · 열 {len(SIM['coef'])}개"
      f" · 절편 {SIM['intercept']:.4f} · 기준 하루 {SIM_BASE}명(준비 {SIM_BASE + EXTRA}인분)")
print("  불러오기 확인: " + " · ".join(f"{label} {v}명" for label, v in SIM_CHECK)
      + (" = 다음 주 예보 카드와 같음" if OUR == "선형 회귀" else ""))
print("구역 순서: 머리 → 다음 주 예보 → 만약에 → 예보 성적표 → 영양사님 감 검증")
print(f"저장: {OUT}")
