#!/usr/bin/env python3
"""Floorplan render (pre-placement, from the kit's floorplan.json + spec): macros with their read (LEF W: rd_out,
addresses, clk) and write (LEF E: wd, mask) faces, the lane-logic / write channels, the spine and the pin windows.
usage: render_fp.py KIT_DIR OUT.png OUT_stats.json"""
import json, sys, re
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.patches as P
kit, out, sout = sys.argv[1:4]
f = json.load(open(f'{kit}/floorplan.json')); s = json.load(open(f'{kit}/spec.json'))
W, H = s['outline']['w'], s['outline']['h']
fig, ax = plt.subplots(figsize=(13, 13 * H / W + 1.2))
ax.add_patch(P.Rectangle((0, 0), W, H, fc='#f7f7f7', ec='k', lw=1))
ma = 0; lanes = {}
for b in f['blocks']:
    x, y, w, h, o = b['x'], b['y'], b['w'], b['h'], b.get('orient', 'R0')
    ma += w * h
    m = re.search(r'g_event_mem\?(\d+)\?', b['inst']); lane = m.group(1) if m else ('gap' if 'gap' in b['inst'] else 'ret')
    lanes.setdefault(lane, []).append((x, y, w, h))
    ax.add_patch(P.Rectangle((x, y), w, h, fc='#9ec5ea', ec='#1f4e79', lw=.5))
    rd_w = o in ('R0', 'MX')             # LEF W face (read) stays W
    ax.add_patch(P.Rectangle((x if rd_w else x + w - 1.5, y), 1.5, h, fc='#d62728', lw=0))
    ax.add_patch(P.Rectangle((x + w - 1.5 if rd_w else x, y), 1.5, h, fc='#2ca02c', lw=0))
for lane, rs in lanes.items():
    x0 = min(r[0] for r in rs); y0 = min(r[1] for r in rs); x1 = max(r[0] + r[2] for r in rs); y1 = max(r[1] + r[3] for r in rs)
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, f'L{lane}' if lane.isdigit() else lane, ha='center', va='center', fontsize=7,
            rotation=90)
for nm, (a, b) in s['pin_ranges'].items():
    face = 'S' if nm in s['pins'].get('S', []) else 'N'
    yy = -4 if face == 'S' else H + 1
    ax.add_patch(P.Rectangle((a, yy), b - a, 3, fc='#ff7f0e', ec='none'))
    ax.text((a + b) / 2, yy - 5 if face == 'S' else yy + 5, nm, ha='center', fontsize=6, rotation=0)
sp = s.get('_spine')
ax.set_xlim(-10, W + 10); ax.set_ylim(-16, H + 16); ax.set_aspect('equal')
std = s.get('std_area_um2', 0)
free = W * H - ma
st = dict(element=s['name'], outline_um=[W, H], area_um2=round(W * H), macros=len(f['blocks']),
          macro_area_pct=round(100 * ma / (W * H), 1), std_area_um2=std, std_fill_of_free_pct=round(100 * std / free, 1),
          findings=f['findings'], vs_c21n=dict(outline_um=[561.6, 388.8], area_um2=round(561.6 * 388.8),
          std_fill_of_free_pct=5.96, empty_area_pct=86.7, pin_to_reg_p90_um=233.7))
ax.set_title(f"{s['name']} floorplan (pre-place)  {W} x {H} um = {W*H:.0f} um2 (c21n 561.6 x 388.8 = 218,350)\n"
             f"84 SRAM 64x16: red = read face (rd_out/addr/clk), green = write face (wd/mask); orange = pin windows\n"
             f"macros {st['macro_area_pct']}% of outline; synth std {std:.0f} um2 = {st['std_fill_of_free_pct']}% of free area",
             fontsize=9)
plt.savefig(out, dpi=130, bbox_inches='tight'); json.dump(st, open(sout, 'w'), indent=1); print(json.dumps(st)[:400])
