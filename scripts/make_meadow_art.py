"""풀숲 픽셀 그림(SVG) 생성기. 같은 씨앗이면 같은 그림이 나온다.
사용: python -m scripts.make_meadow_art   (결과: web/assets/*.svg)
"""
import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "web" / "assets"


def svg(w, h, grid, note):
    """grid: {(x, y): color} → 같은 색 가로 연속 칸을 rect 하나로 합친 SVG"""
    rows = {}
    for (x, y), c in grid.items():
        rows.setdefault((y, c), []).append(x)
    rects = []
    for (y, c), xs in sorted(rows.items()):
        xs.sort()
        start = prev = xs[0]
        for x in xs[1:] + [None]:
            if x is not None and x == prev + 1:
                prev = x
                continue
            rects.append(f'<rect x="{start}" y="{y}" width="{prev - start + 1}" height="1" fill="{c}"/>')
            if x is not None:
                start = prev = x
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" shape-rendering="crispEdges">\n'
            f'  <!-- {note} (손으로 고치지 말고 scripts/make_meadow_art.py로 다시 만들 것) -->\n  '
            + "\n  ".join(rects) + "\n</svg>\n")


def put(grid, w, h, x, y, c):
    if 0 <= y < h:
        grid[(x % w, y)] = c


# ---------- 1. 먼 숲: 둥근 나무 꼭대기 두 줄 (뒤 줄은 흐리게) ----------
def forest():
    r = random.Random(7)
    w, h = 160, 22
    grid = {}
    far, far_hi = "#A9BE98", "#BFD0AE"     # 멀리 있는 나무 (종이에 섞이는 흐린 초록)
    near, near_hi, near_lo = "#7F9F6C", "#93B37E", "#6C8C5B"
    # 나무 사이로 하늘이 바닥까지 뚫리지 않게 아래쪽은 덤불로 먼저 채운다
    for x in range(w):
        for y in range(13, h):
            put(grid, w, h, x, y, far if y < 17 else near_lo)
    for layer, (base, hi, lo, cy, rr) in enumerate([
        (far, far_hi, far, (9, 12), (5, 8)),
        (near, near_hi, near_lo, (13, 16), (4, 7)),
    ]):
        x = r.randint(0, 6)
        while x < w:
            cx, cyy, rad = x, r.randint(*cy), r.randint(*rr)
            for yy in range(cyy - rad, h):
                for xx in range(cx - rad - 1, cx + rad + 2):
                    dx, dy = xx - cx, yy - cyy
                    inside = dx * dx + dy * dy <= rad * rad + rad if yy < cyy else abs(dx) <= rad
                    if not inside:
                        continue
                    c = base
                    if yy < cyy and dx < 0 and dx * dx + dy * dy >= (rad - 2) ** 2 and dy < -1:
                        c = hi  # 왼쪽 위 가장자리에 빛
                    if layer == 1 and yy >= cyy + 2:
                        c = lo  # 앞 줄 나무 아래는 그늘
                    put(grid, w, h, xx, yy, c)
            x += r.randint(rad, rad + rad // 2 + 2)
    return svg(w, h, grid, "먼 숲: 둥근 나무 두 줄, 160x22칸을 가로 반복")


# ---------- 2. 바닥 풀포기·점: 띠 색에 섞이도록 반투명 ----------
TUFT = [".#...#.", ".#.#.#.", "#..#..#"]
TUFT_S = [".#.#.", "#.#.#"]


def stamp(grid, w, h, x, y, shape, c):
    for dy, row in enumerate(shape):
        for dx, ch in enumerate(row):
            if ch == "#":
                put(grid, w, h, x + dx, y + dy, c)


def tufts():
    r = random.Random(11)
    w, h = 48, 24
    grid = {}
    dark, light = "rgba(31,58,26,0.28)", "rgba(222,240,170,0.30)"
    for _ in range(7):
        stamp(grid, w, h, r.randrange(w), r.randrange(h - 3), r.choice([TUFT, TUFT_S]), dark)
    for _ in range(4):
        stamp(grid, w, h, r.randrange(w), r.randrange(h - 2), TUFT_S, light)
    for _ in range(10):
        put(grid, w, h, r.randrange(w), r.randrange(h), r.choice([dark, light]))
    return svg(w, h, grid, "바닥 풀포기와 점: 48x24칸, 반투명이라 어느 띠 위에서도 어울림")


# ---------- 3. 꽃·조약돌: 드문드문 ----------
def flowers():
    r = random.Random(23)
    w, h = 90, 30
    grid = {}
    kinds = [("#F7F4EC", "#F2D65C"), ("#F2D65C", "#C8432F"), ("#EEC0D5", "#F7F4EC")]  # 흰꽃·노란꽃·분홍꽃
    for _ in range(5):
        x, y = r.randrange(w), r.randrange(1, h - 2)
        petal, center = r.choice(kinds)
        for dx, dy in [(0, -1), (-1, 0), (1, 0), (0, 1)]:
            put(grid, w, h, x + dx, y + dy, petal)
        put(grid, w, h, x, y, center)
        put(grid, w, h, x, y + 2, "#3F6534")  # 줄기
    for _ in range(3):
        x, y = r.randrange(w), r.randrange(h - 2)
        for dx in range(3):
            put(grid, w, h, x + dx, y, "#CFC6A6")
            put(grid, w, h, x + dx, y + 1, "#9C9478")
        put(grid, w, h, x, y, "#E4DCC0")
    return svg(w, h, grid, "꽃과 조약돌: 90x30칸, 드문드문")


# ---------- 4. 햇빛 얼룩: 나뭇잎 사이로 떨어지는 빛 ----------
def sunlight():
    r = random.Random(5)
    w, h = 120, 30
    grid = {}
    for _ in range(4):
        cx, cy = r.randrange(w), r.randrange(4, h - 4)
        rx, ry = r.randint(6, 12), r.randint(2, 4)
        for yy in range(cy - ry, cy + ry + 1):
            for xx in range(cx - rx, cx + rx + 1):
                d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
                if d <= 1:
                    put(grid, w, h, xx, yy, "rgba(255,248,200,0.16)" if d > 0.45 else "rgba(255,248,200,0.26)")
    return svg(w, h, grid, "햇빛 얼룩: 120x30칸, 천천히 흘러감")


# ---------- 5. 앞쪽 키 큰 풀 무더기: 포켓몬을 살짝 가림 ----------
def tall_grass():
    r = random.Random(3)
    w, h = 140, 20
    grid = {}
    dark, mid, light = "#2F5127", "#3F6534", "#6E9A57"
    x = r.randint(4, 20)
    while x < w - 10:
        blades = r.randint(4, 7)
        for b in range(blades):
            bx = x + b * 2 + r.randint(-1, 1)
            bh = r.randint(8, h - 2)
            lean = r.choice([-1, 0, 1])
            c = r.choice([dark, mid, mid])
            for i in range(bh):
                xx = bx + round(lean * (i / bh) ** 2 * 3)
                put(grid, w, h, xx, h - 1 - i, c)
                if i < bh // 3:
                    put(grid, w, h, xx + 1, h - 1 - i, c)  # 아래는 두껍게
            put(grid, w, h, bx + round(lean * 3), h - bh, light)  # 끝에 빛
        x += r.randint(28, 52)
    return svg(w, h, grid, "앞쪽 키 큰 풀 무더기: 140x20칸, 드문드문")


# ---------- 6. 풀 가장자리: 뒤쪽(먼 띠 위)·앞쪽(가까운 띠 위) 들쭉날쭉한 풀잎 ----------
def blade_edge(r, grid, w, h, color, lo, hi, step):
    """칸마다 높이가 다른 뾰족한 풀잎 줄. step칸마다 꼭대기 하나"""
    x = 0
    while x < w:
        peak = r.randint(lo, hi)
        for dx in range(step):
            height = max(1, peak - abs(dx - step // 2) * 2)
            for i in range(h - height, h):
                put(grid, w, h, x + dx, i, color)
        x += step


def grass_back():
    r = random.Random(13)
    w, h = 60, 12
    grid = {}
    blade_edge(r, grid, w, h, "#6A9653", 5, 12, 3)  # = --grass-far
    return svg(w, h, grid, "뒤쪽 풀 가장자리: 60x12칸, 먼 띠 색")


def grass_front():
    r = random.Random(17)
    w, h = 48, 14
    grid = {}
    blade_edge(r, grid, w, h, "#3F6534", 7, 14, 3)  # 뒤 줄: 어두운 풀 (= --grass-dark)
    blade_edge(r, grid, w, h, "#527F40", 3, 9, 4)   # 앞 줄: 가까운 띠 색 (= --grass-near)
    return svg(w, h, grid, "앞쪽 풀 가장자리: 48x14칸, 포켓몬 발을 살짝 가림")


for name, fn in [("forest", forest), ("ground-tufts", tufts), ("ground-flowers", flowers),
                 ("sunlight", sunlight), ("grass-tall", tall_grass),
                 ("grass-back", grass_back), ("grass-front", grass_front)]:
    (OUT / f"{name}.svg").write_text(fn(), encoding="utf-8", newline="\n")
    print(name, "ok")
