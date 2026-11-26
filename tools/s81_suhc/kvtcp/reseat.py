#!/usr/bin/env python3
"""S81-KVTC-PINS: T2B probe seats for a taller kvtc (position-major pins).  Probe-only, not a seating proposal.
Keeps every seat of the base probe except: the 4 kvtc bars (new height H, centred on the old bar band, arrangement
v11 = u0|u1 side by side, or v12 = u0/u1 stacked at one x (fix A)), and any macro the grown bars now overlap, which
moves to the nearest free 4.32-um grid spot (2-um halo) inside the core.
usage: reseat.py BASE_DIR NEW_KVTC_LEF ARR(v11|v12) OUT_DIR"""
import re, sys, shutil, json, math, os
from pathlib import Path
base, lef, arr, out = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
sz = {}
for f in list((base / 'macros').glob('*.lef')) + [lef]:
    t = f.read_text()
    for m in re.finditer(r'^MACRO (\S+)\s.*?SIZE ([\d.]+) BY ([\d.]+)', t, re.S | re.M):
        sz[m.group(1)] = (float(m.group(2)), float(m.group(3)))
W, H = sz['dsfd_su_t_kvtc']
mp = (base / 'macro_place.tcl').read_text()
RX = re.compile(r'^ot_seat \{(\S+)\} ([\d.]+) ([\d.]+)$', re.M)
def master(n):
    for k, m in (('u_kvt', 'dsfd_su_t_kvtc'), ('u_relay', 'dsfd_su_t_kvi'), ('g_npc.u_kve', 'dsfd_su_t_kvec'),
                 ('g_rpc.u_kve', 'dsfd_su_t_kvpc'), ('u_kvq', 'dsfd_su_t_kvq'), ('u_cn_write', 'dsfd_su_t_cnw'),
                 ('u_ik_write', 'dsfd_su_t_ikw'), ('u_qnh', 'dsfd_su_t_qnh'), ('u_kvr', 'dsfd_su_t_kvr'),
                 ('u_ik_reduce', 'dsfd_su_t_ikr'), ('.u_l', 'dsfd_sl_t_cpl'), ('u_m', 'ot_sram_1r1w2c_32x64_m1')):
        if n.endswith(k) or k in n:
            return m
    raise KeyError(n)
seats = {}
for m in RX.finditer(mp):
    seats[m.group(1)] = [float(m.group(2)), float(m.group(3))]
G = 4.32; HALO = float(os.environ.get("OT_MHALO", 2.0)); BHALO = float(os.environ.get("OT_BHALO", HALO)); CX0, CY0, CX1, CY1 = 4.32, 4.32, 3209.76, 2207.52
snap = lambda v: round(round(v / G) * G, 2)
bars = sorted(n for n in seats if 'u_kvt' in n)
assert len(bars) == 4
ycen = 933.12 + (1045.44 - 933.12) / 2
gap = float(os.environ.get("OT_GAP", 8.64))
yl = snap(ycen - gap / 2 - H); yu = snap(yl + H + gap)
xa, xb = 1550.88, 2268.0
assert xb - xa >= W + 8.64
pos = {'v11': [(xa, yl), (xb, yl), (xa, yu), (xb, yu)], 'v12': [(xa, yl), (xa, yu), (xb, yl), (xb, yu)]}[arr]
for i, n in enumerate(bars):
    assert f'g_u\\[{i}\\]' in n, n
    seats[n] = list(pos[i])
def rect(n, x=None, y=None, hl=None):
    hl = HALO if hl is None else hl
    w, h = sz[master(n)]; x = seats[n][0] if x is None else x; y = seats[n][1] if y is None else y
    return (x - hl, y - hl, x + w + hl, y + h + hl)
def ov(a, b): return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
fixed = {n: rect(n, hl=BHALO) for n in bars}
moved = []
others = [n for n in seats if n not in fixed]
# cells that overlap a bar move; everyone else stays where it is
stay = {n: rect(n) for n in others if not any(ov(rect(n), r) for r in fixed.values())}
mov = [n for n in others if n not in stay]
occ = list(fixed.values()) + list(stay.values())
def free(r):
    return r[0] >= CX0 - HALO and r[1] >= CY0 - HALO and r[2] <= CX1 + HALO and r[3] <= CY1 + HALO and not any(ov(r, o) for o in occ)
for n in sorted(mov, key=lambda n: -sz[master(n)][0] * sz[master(n)][1]):
    x0, y0 = seats[n]; best = None
    for rad in range(1, 400):
        cands = []
        for dx in range(-rad, rad + 1):
            for dy in (-rad, rad) if abs(dx) != rad else range(-rad, rad + 1):
                x, y = snap(x0 + dx * G), snap(y0 + dy * G)
                r = rect(n, x, y)
                if free(r): cands.append((math.hypot(x - x0, y - y0), x, y))
        if cands:
            best = min(cands); break
    assert best, n
    seats[n] = [best[1], best[2]]; occ.append(rect(n)); moved.append((n, x0, y0, best[1], best[2], round(best[0], 2)))
def sub(m):
    x, y = seats[m.group(1)]
    return f"ot_seat {{{m.group(1)}}} {x} {y}"
out.mkdir(parents=True, exist_ok=True)
txt = RX.sub(sub, mp)
txt = f"# S81-KVTC-PINS probe seats: kvtc {W} x {H} position-major, bars {arr}, {len(moved)} displaced macros moved (reseat.py)\n" + txt
(out / 'macro_place.tcl').write_text(txt)
(out / 'reseat.json').write_text(json.dumps(dict(kvtc=[W, H], arr=arr, gap=gap, bar_halo=BHALO, macro_halo=HALO, bars={n: seats[n] for n in bars}, moved=moved), indent=1) + "\n")
print("bars", {n: seats[n] for n in bars}, "moved", len(moved), "max move", max((m[5] for m in moved), default=0))
