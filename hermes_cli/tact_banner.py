"""Dexall TACT の指揮棒と火花を描画する CLI 起動画面。"""

from __future__ import annotations

import math
import os
import random
import shutil
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console, ConsoleRenderable

PRODUCT_NAME = "Dexall ALL AI5.2 TACT"
WIDTH = 116
HEIGHT = 38
PALETTE = (
    "#345762", "#59858e", "#93c5c7", "#d7f8ef",
    "#515d85", "#7784b5", "#a3acd5", "#e7e4ff",
    "#446269", "#719494", "#a7c5b7", "#d5e8cc",
    "#725e52", "#b88c65", "#edd19a", "#fff3da",
)
FRAMES_PER_BEAT = 18
FRAME_COUNT = 4 * FRAMES_PER_BEAT
PIVOT = (57, 32)
# 画面座標。各ベジェ曲線は次の拍で終わる。下、左、右、上の順に振る。
BEAT_PATH = (
    ((57, 27), (56, 2), (37, 27), (26, 23)),
    ((26, 23), (18, 0), (52, 33), (80, 25)),
    ((80, 25), (93, 22), (98, 16), (91, 11)),
    ((91, 11), (77, 29), (58, 9), (57, 4)),
)
DOWNSTROKE = ((57, 4), (56, 12), (57, 20), (57, 27))


def rotate_point(x, y):
    # 端末セルの縦横比を考慮して画面座標を回転させる。
    cell_aspect = 14 / 7.83
    dx, dy = x - 57, (y - 19) * cell_aspect
    diagonal = math.sqrt(0.5)
    return (58 + (dx - dy) * diagonal * 0.87,
            18.5 + (dx + dy) * diagonal * 0.87 / cell_aspect)


def tip_at(frame):
    phase = frame % FRAME_COUNT / FRAMES_PER_BEAT
    beat = int(phase)
    t = phase - beat
    # 最後の拍は跳ね返りと直線の下振りを組み合わせる。
    if beat == 2:
        if t < 0.36:
            points = BEAT_PATH[2]
            t /= 0.36
        else:
            points = BEAT_PATH[3]
            t = (t - 0.36) / 0.64
    elif beat == 3:
        points = DOWNSTROKE
        t = t ** 1.65
    else:
        points = BEAT_PATH[beat]
    u = 1 - t
    weights = (u**3, 3*u*u*t, 3*u*t*t, t**3)
    return rotate_point(*(sum(w * p[axis] for w, p in zip(weights, points)) for axis in (0, 1)))


def conductor_frame(index):
    rows = [[" "] * WIDTH for _ in range(HEIGHT)]
    colors = [["0"] * WIDTH for _ in range(HEIGHT)]

    def dot(x, y, char, shade):
        x, y = round(x), round(y)
        if 0 <= x < WIDTH and 0 <= y < len(rows):
            rows[y][x] = char
            colors[y][x] = shade

    for sample in range(168, 0, -1):
        delay = sample / 6
        x, y = tip_at(index - delay)
        core = ("#" if delay < 6 else "+" if delay < 16 else ":")
        shade = "7" if delay < 6 else "6" if delay < 16 else "5"
        for dy in (-1, 0, 1):
            for dx in range(-2, 3):
                radius = (dx / 2) ** 2 + (dy / 1.35) ** 2
                if radius <= 1.1:
                    if delay < 17 or radius < 0.65:
                        dot(x + dx, y + dy, core if radius < 0.55 else ".", shade)
        dot(x, y, core, shade)

    # 乱数のシードを周期化し、火花が途切れずループするようにする。
    for age in range(24, -1, -1):
        emission = index - age
        phase = emission % FRAME_COUNT
        burst = phase % FRAMES_PER_BEAT == 0
        if not burst and phase % 2:
            continue
        origin_x, origin_y = tip_at(emission)
        rng = random.Random(5200 + phase)
        count = 18 if burst else 4
        for particle in range(count):
            angle = rng.uniform(0, math.tau)
            speed = rng.uniform(0.42, 1.4) * (1.55 if burst else 1)
            lifetime = rng.randint(12, 24) if burst else rng.randint(6, 15)
            if age >= lifetime:
                continue
            vx, vy = math.cos(angle) * speed, math.sin(angle) * speed * 0.56
            x = origin_x + vx * age
            y = origin_y + vy * age + 0.009 * age ** 2
            brightness = 1 - age / lifetime
            if brightness > 0.68 and particle % 3 == 0:
                streak = "-" if abs(vx) > 2 * abs(vy) else chr(92) if vx * vy > 0 else "/"
                dot(x - vx, y - vy, streak, "d")
            glyph = "*" if brightness > 0.68 else "+" if brightness > 0.38 else "."
            shade = "f" if brightness > 0.80 else "e" if brightness > 0.55 else "d" if brightness > 0.28 else "c"
            dot(x, y, glyph, shade)

    x, y = tip_at(index)
    px, py = rotate_point(*PIVOT)
    slope = x - px
    glyph = "|" if abs(slope) < 4 else "/" if slope > 0 else chr(92)
    for step in range(161):
        t = step / 160
        bx, by = px + (x - px) * t, py + (y - py) * t
        if t < 0.23:
            dot(bx - 1, by, "+", "d")
            dot(bx + 1, by, "+", "d")
            dot(bx, by, "#", "e")
        else:
            dot(bx, by, glyph, "e" if t < 0.8 else "f")
    dot(x - 1, y, "+", "e")
    dot(x + 1, y, "+", "e")
    dot(x, y - 1, ".", "e")
    dot(x, y + 1, ".", "e")
    dot(x, y, "@", "f")
    return ["".join(row).rstrip() for row in rows], ["".join(row) for row in colors]


def spark_preview() -> str:
    """起動後のパネルに収まる静止画を生成する。"""
    rows, _ = conductor_frame(0)
    return "\n".join("".join(row.ljust(WIDTH)[x:x + 2].strip()[:1] or " "
                             for x in range(32, 94, 2)).rstrip()
                      for row in rows[4:34:2]).strip("\n")


def _canvas(frame: int) -> ConsoleRenderable:
    from rich.console import Group
    from rich.text import Text

    rows, shades = conductor_frame(frame)
    header = "DEXALL / AI STAFF".ljust(WIDTH - len(PRODUCT_NAME)) + PRODUCT_NAME
    rule = Text("─" * WIDTH, style="#345762")
    lines = []
    for row, colors in zip(rows, shades):
        line = Text()
        for glyph, shade in zip(row, colors):
            line.append(glyph, PALETTE[int(shade, 16)] if glyph != " " else None)
        lines.append(line)
    return Group(Text(header, style="bold #d7f8ef"), rule, *lines, rule)


def animate_startup(console: Console) -> None:
    """十分に広い対話端末だけで短いアニメーションを再生する。"""
    terminal = shutil.get_terminal_size()
    if (not console.is_terminal or console.no_color
            or os.environ.get("TERM") in (None, "", "dumb")
            or terminal.columns <= WIDTH or terminal.lines < HEIGHT + 4):
        return
    from rich.live import Live

    with Live(console=console, auto_refresh=False, transient=True) as live:
        start = time.monotonic()
        for index, frame in enumerate(range(0, FRAME_COUNT, 6)):
            remaining = start + index / 24 - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)
            live.update(_canvas(frame), refresh=True)
