#!/usr/bin/env python3
"""montage.py OUT.png TITLE  img1::label1  img2::label2 ...  -> labelled grid (4 columns, 420 px cells)"""
import sys
from PIL import Image, ImageDraw, ImageFont
out, title, items = sys.argv[1], sys.argv[2], [a.split('::', 1) for a in sys.argv[3:]]
C = 4 if len(items) > 4 else len(items); R = (len(items) + C - 1) // C; S = 420; LH = 46
try:
    F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 13); FT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 20)
except Exception:
    F = FT = ImageFont.load_default()
M = Image.new('RGB', (C * S, 40 + R * (S + LH)), 'white'); d = ImageDraw.Draw(M)
d.text((10, 8), title, fill='black', font=FT)
for k, (p, lab) in enumerate(items):
    r, c = divmod(k, C); x, y = c * S, 40 + r * (S + LH)
    try:
        im = Image.open(p).convert('RGB'); im.thumbnail((S - 8, S - 8))
        M.paste(im, (x + (S - im.width) // 2, y + (S - im.height) // 2))
    except Exception as e:
        d.text((x + 10, y + 10), 'missing: ' + str(e)[:40], fill='red', font=F)
    lines = []
    for w in lab.split(' '):
        if lines and len(lines[-1]) + len(w) < 60: lines[-1] += ' ' + w
        else: lines.append(w)
    for i, ln in enumerate(lines[:3]):
        d.text((x + 6, y + S + i * 15), ln, fill='black', font=F)
    d.rectangle([x, y, x + S - 1, y + S + LH - 1], outline='#bbbbbb')
M.save(out, optimize=True); print(out, M.size)
