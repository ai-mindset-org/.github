#!/usr/bin/env python3
"""Аватар организации ai-mindset-org — 500×500, знак AIM.

Три варианта: сплошной знак на тёмном поле, он же на бумаге и точечный
(правая половина набрана точками, как на баннере). Плюс контактный лист
с превью в том размере, в котором аватар реально видно в списках GitHub.
"""

import os
from PIL import Image, ImageDraw

SIZE = 500
PAD = 0.14            # поля от стороны квадрата
STEP = 11             # шаг дискретизации для точечного варианта

PALETTE = {
    "dark":  dict(bg=(7, 7, 7), sign=(242, 240, 232), dot=(28, 28, 25)),
    "light": dict(bg=(242, 240, 232), sign=(17, 17, 16), dot=(221, 217, 204)),
}


def load_mask(path="logo.png"):
    """альфа-канал знака, обрезанный по содержимому"""
    im = Image.open(path).convert("RGBA")
    return im.split()[3].crop(im.split()[3].getbbox())


MASK = load_mask()


def dot_field(draw, colour):
    for y in range(12, SIZE, 30):
        for x in range(12, SIZE, 30):
            draw.ellipse((x - 1.4, y - 1.4, x + 1.4, y + 1.4), fill=colour)


def fit(mask):
    """вписать знак в квадрат с полями, вернуть (resized_mask, x0, y0)"""
    box = int(SIZE * (1 - 2 * PAD))
    scale = box / max(mask.size)
    w, h = int(mask.width * scale), int(mask.height * scale)
    return mask.resize((w, h), Image.LANCZOS), (SIZE - w) // 2, (SIZE - h) // 2


def solid(theme):
    p = PALETTE[theme]
    img = Image.new("RGB", (SIZE, SIZE), p["bg"])
    dot_field(ImageDraw.Draw(img), p["dot"])
    m, x0, y0 = fit(MASK)
    img.paste(Image.new("RGB", m.size, p["sign"]), (x0, y0), m)
    return img


def dotted(theme):
    """знак точками: левая половина плотнее, правая разрежена — намёк на разлёт"""
    p = PALETTE[theme]
    img = Image.new("RGB", (SIZE, SIZE), p["bg"])
    d = ImageDraw.Draw(img)
    dot_field(d, p["dot"])
    m, x0, y0 = fit(MASK)
    px = m.load()
    split = m.width * 0.52
    for y in range(0, m.height, STEP):
        for x in range(0, m.width, STEP):
            if px[x, y] < 128:
                continue
            r = 3.4 if x <= split else 2.8
            cx, cy = x0 + x, y0 + y
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=p["sign"])
    return img


def contact_sheet(files):
    """превью: как аватар выглядит в 260, 96 и 40 пикселей"""
    BIG, MID, SMALL = 260, 96, 40
    pad, gap, col = 26, 44, 260 + 14 + 96
    w = pad * 2 + len(files) * col + (len(files) - 1) * gap
    h = pad * 2 + BIG + 34
    sheet = Image.new("RGB", (w, h), (13, 17, 23))
    draw = ImageDraw.Draw(sheet)
    x = pad
    for f in files:
        im = Image.open(f)
        sheet.paste(im.resize((BIG,) * 2, Image.LANCZOS), (x, pad))
        sheet.paste(im.resize((MID,) * 2, Image.LANCZOS), (x + BIG + 14, pad))
        sheet.paste(im.resize((SMALL,) * 2, Image.LANCZOS), (x + BIG + 14, pad + MID + 16))
        draw.text((x, pad + BIG + 12), os.path.basename(f), fill=(139, 148, 158))
        x += col + gap
    return sheet


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    made = []
    for name, img in (
        ("avatar-dark.png", solid("dark")),
        ("avatar-light.png", solid("light")),
        ("avatar-dots-dark.png", dotted("dark")),
    ):
        path = os.path.join(here, name)
        img.save(path)
        made.append(path)
        print(f"{path}  {os.path.getsize(path)} bytes")
    sheet = os.path.join(here, "preview", "avatars.png")
    contact_sheet(made).save(sheet)
    print(sheet)
