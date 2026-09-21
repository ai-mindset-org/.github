#!/usr/bin/env python3
"""AI Mindset org banner, variant B — the mark with its right half scattering.

Same motion idea as the hero on aimindset-main.web.app: the sign is sampled into
dots, the right half flies apart and comes back. Baked as SMIL (animateTransform
with three keys per dot) so GitHub renders it through camo.
"""

import math
from PIL import Image

W, H = 1200, 400
DUR = "6s"
MONO = "ui-monospace,'SFMono-Regular',Menlo,Consolas,'Liberation Mono',monospace"

# знак: центр и размер на полотне баннера
MARK_CX, MARK_CY, MARK_SIZE = 948, 202, 248
STEP = 13            # шаг дискретизации исходного png
SCATTER = (34, 104)  # разброс амплитуды разлёта

THEMES = {
    "dark": dict(
        bg="#070707", dot="#191917", frame="#1f1f1c", mark="#8a8a82",
        text="#f2f0e8", muted="#8a8a82", faint="#55554f",
        sign="#f2f0e8", accent="#D92027",
    ),
    "light": dict(
        bg="#f2f0e8", dot="#ddd9cc", frame="#d3cfc0", mark="#6b6a62",
        text="#111110", muted="#5c5b54", faint="#8a8880",
        sign="#111110", accent="#D92027",
    ),
}


def sample_logo(path="logo.png"):
    """png → точки по альфе, приведённые к координатам баннера"""
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = im.load()
    pts = []
    for y in range(0, h, STEP):
        for x in range(0, w, STEP):
            if px[x, y][3] > 128:
                pts.append((x, y))
    if not pts:
        raise SystemExit("logo.png: нет непрозрачных пикселей")
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    scale = MARK_SIZE / max(x1 - x0, y1 - y0)
    out = []
    for x, y in pts:
        out.append((MARK_CX + (x - (x0 + x1) / 2) * scale,
                    MARK_CY + (y - (y0 + y1) / 2) * scale))
    return out


DOTS = sample_logo()
SPLIT = MARK_CX + 4      # вертикальная черта знака — граница половин


def lcg(seed=13):
    state = seed
    def rnd():
        nonlocal state
        state = (state * 1103515245 + 12345) % 2147483648
        return state / 2147483648
    return rnd


def build(theme_name):
    t = THEMES[theme_name]
    rnd = lcg()
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="AI Mindset — labs, platform, community, special projects">',
        f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>',
    ]

    dots = []
    for y in range(14, H, 24):
        for x in range(14, W, 24):
            dots.append(f'<circle cx="{x}" cy="{y}" r="1"/>')
    out.append(f'<g fill="{t["dot"]}">' + "".join(dots) + "</g>")

    out.append(f'<rect x="18.5" y="18.5" width="{W-37}" height="{H-37}" fill="none" '
               f'stroke="{t["frame"]}" stroke-width="1"/>')
    m, L = 18, 17
    for d in (f'M{m} {m+L} V{m} H{m+L}', f'M{W-m-L} {m} H{W-m} V{m+L}',
              f'M{m} {H-m-L} V{H-m} H{m+L}', f'M{W-m-L} {H-m} H{W-m} V{H-m-L}'):
        out.append(f'<path d="{d}" fill="none" stroke="{t["mark"]}" stroke-width="1"/>')

    # ── знак ────────────────────────────────────────────────────────────────
    out.append(f'<g fill="{t["sign"]}">')
    for x, y in DOTS:
        r = 1.9
        if x <= SPLIT:                                   # левая половина держит форму
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" opacity="0.92"/>')
            continue
        # правая: вектор наружу от центра знака + разброс
        ang = math.atan2(y - MARK_CY, x - MARK_CX) + (rnd() - 0.5) * 0.9
        amp = SCATTER[0] + rnd() * (SCATTER[1] - SCATTER[0])
        dx, dy = math.cos(ang) * amp * 0.92, math.sin(ang) * amp * 0.62
        spin = (rnd() - 0.5) * 18
        keys = f'0;{0.44};1'
        splines = "0.16 0.8 0.3 1;0.5 0 0.2 1"           # быстрый выброс, мягкий возврат
        out.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" opacity="0.92">'
            f'<animateTransform attributeName="transform" type="translate" '
            f'values="0 0;{dx:.1f} {dy + spin:.1f};0 0" keyTimes="{keys}" '
            f'dur="{DUR}" calcMode="spline" keySplines="{splines}" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0.92;0.30;0.92" keyTimes="{keys}" '
            f'dur="{DUR}" calcMode="spline" keySplines="{splines}" repeatCount="indefinite"/>'
            f'<animate attributeName="r" values="{r};{r*0.7:.2f};{r}" keyTimes="{keys}" '
            f'dur="{DUR}" calcMode="spline" keySplines="{splines}" repeatCount="indefinite"/>'
            f'</circle>')
    out.append("</g>")

    # ── текст ───────────────────────────────────────────────────────────────
    out.append(f'<g font-family="{MONO}">')
    out.append(f'<text x="72" y="62" font-size="15" letter-spacing="2.2" fill="{t["muted"]}">'
               f'ai mindset · labs, platform, community, special projects</text>')
    out.append(f'<text x="{W-72}" y="62" text-anchor="end" font-size="15" letter-spacing="2.2" '
               f'fill="{t["muted"]}">aimindset.org</text>')
    out.append(f'<text x="70" y="212" font-size="84" font-weight="700" letter-spacing="-1.5" '
               f'fill="{t["text"]}">AI Mindset</text>')
    pulse = [0.72 + 0.28 * math.sin(2 * math.pi * (i / 24) * 2) for i in range(25)]
    vals = ";".join(f"{v:.3f}" for v in pulse)
    ktimes = ";".join(f"{i/24:.4f}" for i in range(25))
    out.append(f'<rect x="72" y="232" width="150" height="4" fill="{t["accent"]}">'
               f'<animate attributeName="opacity" values="{vals}" keyTimes="{ktimes}" '
               f'dur="{DUR}" repeatCount="indefinite" calcMode="linear"/></rect>')
    out.append(f'<text x="72" y="278" font-size="17" letter-spacing="0.6" fill="{t["faint"]}">'
               f'&gt;25 labs · 1600+ participants · 30+ countries · 4 years</text>')
    out.append(f'<text x="72" y="{H-42}" font-size="16" letter-spacing="1.4" fill="{t["muted"]}">'
               f'aimindset.org · t.me/ai_mind_set</text>')
    out.append("</g>")

    out.append("</svg>")
    return "".join(out)


if __name__ == "__main__":
    import io, os
    here = os.path.dirname(os.path.abspath(__file__))
    print(f"dots: {len(DOTS)} (right half: {sum(1 for x, _ in DOTS if x > SPLIT)})")
    for name in THEMES:
        path = os.path.join(here, f"banner-{name}.svg")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(build(name))
        print(f"{path}  {os.path.getsize(path)} bytes")
