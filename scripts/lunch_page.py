"""3일차 실습 C: 한빛식당(가상) 밥 예보 페이지 — 깨끗한 표로 계산해 HTML 한 장을 쓴다 (손으로 고치지 않음).

실행: uv run python scripts/lunch_page.py
입력: workbench/day3/outputs/lunch_clean.csv · labs/day3/lab-c/nutritionist_memo.md (읽기만)
결과: workbench/day3/outputs/hanbit_lunch.html
근거: labs/day3/lab-c/lab_c_guide.md 「5. 감 검증」 · 「6. 페이지 규칙」
지금 구역: 머리 → 영양사님 감 검증. 같은 입력이면 같은 페이지(시각 · 난수 없음).
"""
import html
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
CLEAN = "workbench/day3/outputs/lunch_clean.csv"
MEMO = "labs/day3/lab-c/nutritionist_memo.md"
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
"""


def page(body):
    data = json.dumps({"charts": charts}, ensure_ascii=False).replace("</", "<\\/")
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


# 구역 순서: 머리 → (다음 단계에서 머리 바로 아래에 구역을 더한다) → 영양사님 감 검증
sections = [section_head(), section_beliefs()]
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(page("".join(sections)), encoding="utf-8")

print(f"기록 기간 {PERIOD[0]} ~ {PERIOD[1]} · 깨끗한 표 {len(df)}일 · 비교 바탕(행사 없고 월급날 아님) {len(base)}일")
for b in beliefs:
    nums = " vs ".join(f"{g['name']} {g['value']:.1f}({g['days']}일)" for g in b["groups"])
    print(f"믿음 {b['no']}: {nums} · 믿음 방향 차이 {b['diff']:+.2f} → {b['verdict']}")
print("  메뉴 순위: " + " > ".join(f"{g['name']} {g['value']:.1f}({g['days']}일)" for g in menus))
print(f"월급날: {payday['name']} {payday['value']:.1f}({payday['days']}일) vs {normal['name']} {normal['value']:.1f}"
      f"({normal['days']}일) · 차이 {pay_diff:+.2f} → {pay_text}")
print(f"저장: {OUT}")
