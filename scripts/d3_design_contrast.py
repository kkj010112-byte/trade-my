"""3일차 실습 D: design.md 토큰의 글자-바탕 대비(WCAG 2.x 상대 휘도 공식)를 계산한다.

실행: uv run python scripts/d3_design_contrast.py
기준: 4.5 : 1 이상이면 통과.
v2(B 다크 금융 터미널) 색. C안 색은 design_v2c.md에 남아 있다. v1 색은 design.md 5절 아래 'v1 대비' 줄에 남겨 둔다.
"""

TOKENS = {
    "bg": "#0D131E",
    "surface": "#141C2A",
    "border": "#2A3546",
    "text": "#E7EBF1",
    "text-muted": "#9BA6B5",
    "accent": "#8CC0E8",
    "grade-s": "#5CC08A",
    "grade-a": "#B9C653",
    "grade-b": "#E9A452",
    "grade-c": "#F2766B",
    "grade-on": "#0D131E",
    # 지역 타일 · 히트맵(v3, 7절 ③)
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
    # 경영진 한 장(v3, 7절 ④): 흑백 인쇄
    "print-bg": "#FFFFFF",
    "print-text": "#111111",
    "print-muted": "#444444",
}


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    rgb = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(fg: str, bg: str) -> float:
    l1, l2 = sorted([luminance(TOKENS[fg]), luminance(TOKENS[bg])], reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


PAIRS = [
    ("제목 · 본문(페이지 바탕)", "text", "bg"),
    ("본문 · 표 값(판 위)", "text", "surface"),
    ("KPI 숫자(판 위)", "text", "surface"),
    ("KPI 숫자(C등급 채권, 판 위)", "grade-c", "surface"),
    ("보조 글자 · KPI 라벨(판 위)", "text-muted", "surface"),
    ("기준일(페이지 바탕)", "text-muted", "bg"),
    ("표 머리(판 위)", "text-muted", "surface"),
    ("슬라이더 라벨(판 위)", "text-muted", "surface"),
    ("슬라이더 값 · 차이 숫자(판 위)", "accent", "surface"),
    ("바닥글(페이지 바탕)", "text-muted", "bg"),
    ("등급 S 라벨(어두운 글자 / S 면)", "grade-on", "grade-s"),
    ("등급 A 라벨(어두운 글자 / A 면)", "grade-on", "grade-a"),
    ("등급 B 라벨(어두운 글자 / B 면)", "grade-on", "grade-b"),
    ("등급 C 라벨(어두운 글자 / C 면)", "grade-on", "grade-c"),
    # 7절 ① 상세 패널(패널 면 = 페이지 바탕색)
    ("패널 값 · 신호(패널 위)", "text", "bg"),
    ("패널 항목 이름 · 고정 한 줄(패널 위)", "text-muted", "bg"),
    ("'확인 필요' 단추 · '확인 완료' 표시(패널 · 고른 줄 위)", "accent", "bg"),
    ("'확인 완료' 단추(채운 면)", "bg", "accent"),
    ("'확인 완료' 표시(고르지 않은 줄 · 판 위)", "accent", "surface"),
    # 7절 ③ 지역 타일(진하기 4단계) · 히트맵
    ("타일 1단계(C 비중 10% 미만)", "heat-c-on-1", "heat-c-1"),
    ("타일 2단계(10–25%)", "heat-c-on-2", "heat-c-2"),
    ("타일 3단계(25–50%)", "heat-c-on-3", "heat-c-3"),
    ("타일 4단계(50% 이상)", "heat-c-on-4", "heat-c-4"),
    ("히트맵 연한 칸 S", "text", "grade-s-soft"),
    ("히트맵 연한 칸 A", "text", "grade-a-soft"),
    ("히트맵 연한 칸 B", "text", "grade-b-soft"),
    ("히트맵 연한 칸 C", "text", "grade-c-soft"),
    ("히트맵 빈칸 '–'(판 위)", "text-muted", "surface"),
    ("지역 이름 · 범례(판 위)", "text", "surface"),
    # 7절 ④ 경영진 한 장(인쇄 · 한 장 보기)
    ("인쇄 본문 · KPI 숫자 · 등급 라벨", "print-text", "print-bg"),
    ("인쇄 보조 글자 · 표 머리 · 바닥글", "print-muted", "print-bg"),
]

if __name__ == "__main__":
    print("| 짝 | 글자 | 바탕 | 대비 | 4.5 이상 |")
    print("|---|---|---|---:|---|")
    rs = []
    for name, fg, bg in PAIRS:
        r = contrast(fg, bg)
        rs.append(r)
        print(f"| {name} | `{fg}` {TOKENS[fg]} | `{bg}` {TOKENS[bg]} | {r:.2f} : 1 | {'예' if r >= 4.5 else '아니오'} |")
    print(f"\n가장 낮은 값: {min(rs):.2f} : 1")
