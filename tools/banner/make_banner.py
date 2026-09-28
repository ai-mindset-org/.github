"""AIM org banner: the voxel mark from voxel_object.blend, frontal, 853 cubes.

Every cube is its own object: it starts in a cloud around the mark and flies into
place with a turn, left half first. Motion is SMIL (animate + animateTransform, fill
freeze, plays once) because GitHub strips <script> and CSS animation through camo is
unreliable. Text is converted to outlines, so no fonts load on GitHub.

Run: python make_banner.py  -> writes ../../profile/banner-{light,dark}.svg
Needs: pip install fonttools brotli
"""
import json
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

F = {'mono400': TTFont('fonts/aim-plex-400.woff2'), 'mono600': TTFont('fonts/aim-plex-600.woff2'),
     'grot700': TTFont('fonts/SpaceGrotesk-700.ttf')}

def text(s, x, y, size, font, fill, track=0.0):
    f = F[font]; gs = f.getGlyphSet(); cmap = f.getBestCmap(); k = size / f['head'].unitsPerEm
    pen = SVGPathPen(gs); cx = x
    for ch in s:
        g = cmap.get(ord(ch))
        if g is None: continue
        gs[g].draw(TransformPen(pen, (k, 0, 0, -k, cx, y)))
        cx += gs[g].width * k + track
    return f'<path fill="{fill}" d="{pen.getCommands()}"/>', cx

W, H = 1200, 400
RED = '#e8403a'
THEME = {
    False: dict(bg='#f7f7f7', ink='#1c1c1e', sec='#707075', div='#dcdcde',
                face=('#f3f3f3', '#d9d9db'), hi='#ffffff', lo='#adadb1', sh='#000000', sho=.26, cto=.30),
    True:  dict(bg='#111214', ink='#f2f2f3', sec='#96969c', div='#2b2c30',
                face=('#e9e9ea', '#c9c9cc'), hi='#ffffff', lo='#9d9da2', sh='#000000', sho=.55, cto=.5),
}
import math
BC = json.load(open('blender-cubes.json'))
PITCH = 0.16
CELLS = []
for side, cs in BC.items():
    for (x, y, z, sx, sy, sz) in cs:
        CELLS.append((round((x + 2.646) / PITCH), round((7.44 - z) / PITCH), sx / PITCH))
CELLS = sorted({(c, r): s for c, r, s in CELLS}.items())
COLS = max(c for (c, r), s in CELLS) + 1; ROWS = max(r for (c, r), s in CELLS) + 1

def rnd(i, k):
    v = math.sin(i * 12.9898 + k * 78.233) * 43758.5453
    return v - math.floor(v)

def logo(t, x0, y0, u):
    cubes = []
    for i, ((c, r), s) in enumerate(CELLS):
        w = u * s; x = x0 + c * u + (u - w) / 2; y = y0 + r * u + (u - w) / 2
        ang = rnd(i, 1) * 2 * math.pi; dist = 90 + rnd(i, 2) * 260
        tx = math.cos(ang) * dist + 120; ty = math.sin(ang) * dist * 0.7 - 30
        rot = (rnd(i, 3) - .5) * 360
        delay = int(200 + (c / COLS) * 1500 + rnd(i, 4) * 700)
        b = max(0.8, w * 0.1)
        cx, cy = x + w / 2, y + w / 2
        bs = f'{delay / 1000:.2f}s'
        cubes.append(
            f'<g opacity="0">'
            f'<animate attributeName="opacity" from="0" to="1" begin="{bs}" dur="0.35s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" values="{tx:.0f} {ty:.0f};0 0" '
            f'begin="{bs}" dur="1.5s" calcMode="spline" keyTimes="0;1" keySplines=".22 1 .36 1" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="rotate" additive="sum" values="{rot:.0f} {cx:.1f} {cy:.1f};0 {cx:.1f} {cy:.1f}" '
            f'begin="{bs}" dur="1.5s" calcMode="spline" keyTimes="0;1" keySplines=".22 1 .36 1" fill="freeze"/>'
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{w:.2f}" fill="url(#f)"/>'
            f'<path fill="{t["hi"]}" d="M{x:.2f} {y:.2f}h{w:.2f}l-{b:.2f} {b:.2f}h-{w-2*b:.2f}v{w-2*b:.2f}l-{b:.2f} {b:.2f}z"/>'
            f'<path fill="{t["lo"]}" d="M{x+w:.2f} {y+w:.2f}h-{w:.2f}l{b:.2f} -{b:.2f}h{w-2*b:.2f}v-{w-2*b:.2f}l{b:.2f} -{b:.2f}z"/>'
            '</g>')
    return (f'<g filter="url(#s)">' + ''.join(cubes) + '</g>'), len(cubes)

def banner(dark):
    t = THEME[dark]
    css = ''
    defs = (f'<defs><linearGradient id="f" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="{t["face"][0]}"/><stop offset="1" stop-color="{t["face"][1]}"/></linearGradient>'
            f'<filter id="s" x="-20%" y="-20%" width="150%" height="150%">'
            f'<feDropShadow dx="7" dy="10" stdDeviation="9" flood-color="{t["sh"]}" flood-opacity="{t["sho"]}" result="a"/>'
            f'<feDropShadow in="a" dx="2" dy="3" stdDeviation="1.4" flood-color="{t["sh"]}" flood-opacity="{t["cto"]}"/></filter></defs>')
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
         'aria-label="AIM – labs, platform, community, special projects">',
         '<title>AIM – labs, platform, community, special projects</title>', css, defs,
         f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>']
    L = 72
    p.append(text('AI MINDSET  /  GITHUB', L, 58, 17, 'mono400', t['sec'], 1.2)[0])
    p.append(text('AIM', L - 4, 150, 104, 'grot700', RED, -2)[0])
    p.append(text('labs · platform', L, 202, 36, 'mono600', t['ink'])[0])
    p.append(text('community · projects', L, 246, 36, 'mono600', t['ink'])[0])
    p.append(text('25+ labs · 4 years · 1600+ participants', L, 282, 19, 'mono400', t['sec'])[0])
    p.append(f'<rect x="{L}" y="304" width="600" height="1.5" fill="{t["div"]}"/>')
    p.append(text('small tools · apps.aimindset.org', L, 342, 24, 'mono600', t['ink'])[0])
    u = 7.4
    lg, n = logo(t, W - 120 - COLS * u, (H - ROWS * u) / 2, u)
    p.append(lg); p.append('</svg>')
    return ''.join(p), n

for dark, name in ((False, 'light'), (True, 'dark')):
    s, n = banner(dark)
    open(f'../../profile/banner-{name}.svg', 'w', encoding='utf8').write(s)
    print(name, len(s), 'cubes', n)
