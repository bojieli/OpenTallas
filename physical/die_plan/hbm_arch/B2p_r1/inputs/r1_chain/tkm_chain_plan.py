#!/usr/bin/env python3
"""PATH-HBM: structural TKM chain floorplan for root.u_tkm_SW (root core + 32 common tiles).

Fix for the root<->tile0 seam FAIL and the scattered tile chain: the common tile gets a straight-through
chain template (S: clr, conv, ins_v, ins_b[i], up_out[i]; N: ovf_v, ovf_b[i], up_in[i] at the SAME x), so
vertically stacked tiles connect face to face; columns alternate R0 / MX (snake), turns are one column pitch.
The root core's N tile0 pins copy the tile S x bit for bit. 0 added cycles: every hop is face flop -> face flop.
Outputs (dir of this script): tkm_tile_pins_chain.json, tkm_root_pins_chain.json, tkm_chain_placement.json,
tkm_chain_audit.json, tkm_chain_plan.png.
"""
import json, math, sys
from pathlib import Path

P = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/home/ubuntu/scratch/codex-hbm-0719')
W, H = 319.68, 345.6
PART = (1382.4, 5356.8)
REACH = 405.0
HALO = 8.64

rp = json.load(open(SRC / 'tkm_root_pins.json'))
tp = json.load(open(SRC / 'tkm_tile_pins.json'))
plan = json.load(open(P / 'path_hbm_root.json'))
NB = 344

# ---- common tile template (R0 frame) ----
x0, dx = 10.584, 0.384          # M5 grid (0.048 pitch, 8 tracks); 691 slots span 10.584..275.544 (root N ctl pins stay at 298.6..317.4)
slots = [round(x0 + j * dx, 3) for j in range(3 + 2 * NB)]
S = {'tile_clr': [slots[0]], 'tile_conv_o': [slots[1]], 'tile_ins_v': [slots[2]],
     'tile_ins_b': [slots[3 + 2 * i] for i in range(NB)], 'tile_up_out': [slots[4 + 2 * i] for i in range(NB)]}
Npairs = {'tile_ovf_v': S['tile_ins_v'], 'tile_ovf_b': S['tile_ins_b'], 'tile_up_in': S['tile_up_out'],
          'tile_clr_o': S['tile_clr'], 'tile_conv': S['tile_conv_o']}   # TOKEN 10-25: clr systolic down, conv relayed up
tile = []
# GEOM PASS-COND (1): alternate M5/M3. Lattice: M5 x = 0.024 + 0.048k (slots already on it), M3 x = 0.018 + 0.036k (snap odd slots)
snap = lambda v, off, pit: round(off + round((v - off) / pit) * pit, 3)
slots = [x if j % 2 == 0 else snap(x, 0.018, 0.036) for j, x in enumerate(slots)]
S = {k: [slots[[round(x0 + j * dx, 3) for j in range(len(slots))].index(x)] for x in v] for k, v in S.items()}
Npairs = {k: [slots[[round(x0 + j * dx, 3) for j in range(len(slots))].index(x)] for x in v] for k, v in Npairs.items()}
LAY = {x: ('M5' if j % 2 == 0 else 'M3') for j, x in enumerate(slots)}
for bus, xs in S.items():
    for i, x in enumerate(xs):
        tile.append(dict(bus=bus, bit=(i if len(xs) > 1 else None), layer=LAY[x], x=x, y=0.0, face='S'))
for bus, xs in Npairs.items():
    for i, x in enumerate(xs):
        tile.append(dict(bus=bus, bit=(i if len(xs) > 1 else None), layer=LAY[x], x=x, y=H, face='N'))
for p in tp:   # ID strap and clock stay on N, M7 (clock moved to mid face per Codex/CLOCK note)
    if p['bus'] == 'tile_tid':
        tile.append(dict(p, layer='M7', x=round(150.112 + 0.576 * (p['bit'] or 0), 3)))   # M7 x = 0.032 + 0.064k
tile.append(dict(bus='tile_clk', bit=None, layer='M7', x=159.84, y=H, face='N'))
old = {(p['bus'], p['bit']) for p in tp}
new = {(p['bus'], p['bit']) for p in tile}
assert new - old == {('tile_clr_o', None), ('tile_conv_o', None)} and old - new == set(), (old ^ new)
assert len({(p['face'], p['layer'], p['x']) for p in tile}) == len(tile), 'pin overlap'

# ---- root core: tile0 buses on N copy the tile S x bit for bit ----
rmap = {'tile_clr': 'clr', 'tile_conv': 'conv', 'tile_ins_v': 'ins_v', 'tile_ins_b': 'ins_b', 'tile_up_out': 'up_out'}
tx = {(p['bus'], p['bit']): p['x'] for p in tile if p['face'] == 'S'}
root = []
for p in rp:
    q = dict(p)
    if '_e86_u_tile_' in p['bus']:
        tb = 'tile_' + p['bus'].split('_e86_u_tile_')[1]
        if tb == 'tile_conv':
            tb = 'tile_conv_o'    # same S slot; root conv = tree source to tile31 (pin stays at this N site)
        q['x'] = tx[(tb, p['bit'])]; q['layer'] = LAY[q['x']]
    root.append(q)
# root W face: del_flit (2047, was E: faced the partition E edge behind the tile wall) + w_* (569) share W, M4/M6
# alternating, so the NW L74 delivery and the L12/L13 return both face the open area west/south of the root column.
wl = [p for p in root if p['face'] == 'E'] + [p for p in root if p['face'] == 'W']
for j, q in enumerate(wl):
    q['face'] = 'W'; q['x'] = 0.0; q['layer'] = 'M4' if j % 2 == 0 else 'M6'
    q['y'] = round(2.184 + (j // 2) * 0.24, 3) if j % 2 == 0 else round(2.208 + (j // 2) * 0.256, 3)   # M4 0.024+0.048k (5 tr), M6 0.032+0.064k (4 tr)
assert max(q['y'] for q in wl) < H - 2
rN = [p for p in root if p['face'] == 'N']
assert len({(p['layer'], p['x']) for p in rN}) == len(rN), 'root N overlap (non-tile N pins must avoid 10.58..308.7)'

# ---- placement: snake over 4 columns ----
cols = [1036.8, 708.48, 362.88, 17.28]           # right column (root column) first; 25.92 um E-edge channel kept
pitch = H + HALO                                 # 8.64 um gap between stacked tiles
row0 = 2808.0                                    # top block rows 0..6 (above host_cp_rxs 2730.24 + halo + turn band)
rowy = [row0 + r * pitch for r in range(7)]
top_y = rowy[6]
place = {}
# right column: tiles 0..12 going up, tile12 on the top row; root under tile0
for k in range(13):
    place[k] = (cols[0], top_y - (12 - k) * pitch, 'R0')
root_xy = (cols[0], place[0][1] - pitch)
# column 1 (x=708.48): tiles 13..19 going down (MX); column 2: 20..26 going up (R0); column 3: 27..31 going down (MX)
for j in range(7):
    place[13 + j] = (cols[1], rowy[6 - j], 'MX')
for j in range(7):
    place[20 + j] = (cols[2], rowy[j], 'R0')
for j in range(5):
    place[27 + j] = (cols[3], rowy[6 - j], 'MX')
assert len(place) == 32

def pin_xy(origin, orient, p):
    x, y = p['x'], p['y']
    if orient == 'MX':
        y = H - y
    return (origin[0] + x, origin[1] + y)

# ---- obstacle check (non-TKM hard cores + halo, partition outline) ----
obst = [h for h in plan['root']['hard_cores'] if 'tkm_SW' not in h['inst']]
def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
viol = []
boxes = {('tile%d' % k): (v[0], v[1], v[0] + W, v[1] + H) for k, v in place.items()}
boxes['root'] = (root_xy[0], root_xy[1], root_xy[0] + W, root_xy[1] + H)
for n, b in boxes.items():
    if b[0] < HALO - 1e-6 or b[1] < HALO - 1e-6 or b[2] > PART[0] - HALO + 1e-6 or b[3] > PART[1] - HALO + 1e-6:
        viol.append((n, 'outline'))
    for h in obst:
        o = h['origin_um']; w = h['outline_um']
        if overlap(b, (o[0] - HALO, o[1] - HALO, o[0] + w[0] + HALO, o[1] + w[1] + HALO)):
            viol.append((n, h['inst']))
names = list(boxes)
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        if overlap(boxes[names[i]], boxes[names[j]]):
            viol.append((names[i], names[j]))

# ---- per-bit hop audit ----
def bus_pins(lst, bus):
    return {p['bit']: p for p in lst if p['bus'] == bus}
hops = []
def hop(name, src_o, src_or, src_list, src_bus, dst_o, dst_or, dst_list, dst_bus):
    a, b = bus_pins(src_list, src_bus), bus_pins(dst_list, dst_bus)
    assert a.keys() == b.keys(), (src_bus, dst_bus)
    d = []
    for bit in a:
        pa, pb = pin_xy(src_o, src_or, a[bit]), pin_xy(dst_o, dst_or, b[bit])
        d.append(abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]))
    hops.append(dict(hop=name, src=src_bus, dst=dst_bus, bits=len(d), max_um=round(max(d), 3), over_reach=sum(x > REACH for x in d)))
rb = lambda t: next(p['bus'] for p in root if p['bus'].endswith('_e86_u_tile_' + t))
for t in ('ins_b', 'ins_v', 'clr'):
    hop('root->tile0', root_xy, 'R0', root, rb(t), place[0][:2], place[0][2], tile, 'tile_' + t)
hop('tile0->root', place[0][:2], place[0][2], tile, 'tile_up_out', root_xy, 'R0', root, rb('up_out'))
for k in range(31):
    a, b = place[k], place[k + 1]
    hop('tile%d->tile%d down' % (k, k + 1), a[:2], a[2], tile, 'tile_ovf_b', b[:2], b[2], tile, 'tile_ins_b')
    hop('tile%d->tile%d dv' % (k, k + 1), a[:2], a[2], tile, 'tile_ovf_v', b[:2], b[2], tile, 'tile_ins_v')
    hop('tile%d->tile%d up' % (k + 1, k), b[:2], b[2], tile, 'tile_up_out', a[:2], a[2], tile, 'tile_up_in')
    hop('tile%d->tile%d clr' % (k, k + 1), a[:2], a[2], tile, 'tile_clr_o', b[:2], b[2], tile, 'tile_clr')
    hop('tile%d->tile%d conv' % (k + 1, k), b[:2], b[2], tile, 'tile_conv_o', a[:2], a[2], tile, 'tile_conv')
worst = max(h['max_um'] for h in hops)
over = sum(h['over_reach'] for h in hops)

# clr/conv: plan-level equal-latency registered broadcast (one net each, 32 sinks) from the root core N pin
src = pin_xy(root_xy, 'R0', bus_pins(root, rb('clr'))[None])
far = max(abs(pin_xy(place[k][:2], place[k][2], S_p)[0] - src[0]) + abs(pin_xy(place[k][:2], place[k][2], S_p)[1] - src[1])
          for k in [31] for S_p in [bus_pins(tile, 'tile_conv')[None]])   # conv tree feeds tile31 only
bc_depth = math.ceil(far / REACH)

audit = dict(verdict='PASS' if (not viol and over == 0) else 'FAIL', worst_hop_um=worst, bits_over_reach=over,
             obstacle_violations=viol, root_origin=root_xy, tiles={k: dict(origin=v[:2], orient=v[2]) for k, v in place.items()},
             clr_conv_broadcast=dict(farthest_um=round(far, 1), registered_depth_at_405=bc_depth,
                                     note='conv: registered tree root -> tile31 N conv pin only (TOKEN CB21), then in-tile up relay; clr: systolic down chain (in-tile FT)'),
             hops=hops)
(P / 'tkm_tile_pins_chain.json').write_text(json.dumps(tile, indent=0))
(P / 'tkm_root_pins_chain.json').write_text(json.dumps(root, indent=0))
(P / 'tkm_chain_placement.json').write_text(json.dumps(dict(root=dict(inst='u_tkm_SW_root', origin_um=root_xy, orient='R0'),
    tiles=[dict(inst='u_tkm_SW_tile%d' % k, tile_tid=k, origin_um=list(v[:2]), orient=v[2]) for k, v in sorted(place.items())]), indent=1))
(P / 'tkm_chain_audit.json').write_text(json.dumps(audit, indent=1))
print(json.dumps({k: audit[k] for k in ('verdict', 'worst_hop_um', 'bits_over_reach', 'obstacle_violations', 'root_origin', 'clr_conv_broadcast')}))

# ---- render ----
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig, ax = plt.subplots(figsize=(7, 22))
ax.add_patch(Rectangle((0, 0), *PART, fc='none', ec='black', lw=1.5))
for h in plan['root']['hard_cores']:
    if 'tkm_SW' in h['inst']:
        o, w = h['origin_um'], h['outline_um']
        ax.add_patch(Rectangle(o, *w, fc='none', ec='#bbbbbb', ls=':', lw=0.7))
for h in obst:
    o, w = h['origin_um'], h['outline_um']
    ax.add_patch(Rectangle(o, *w, fc='#dddddd', ec='#666666')); ax.text(o[0] + w[0] / 2, o[1] + w[1] / 2, h['inst'].replace('u_', ''), fontsize=5, ha='center', va='center')
ax.add_patch(Rectangle(root_xy, W, H, fc='#9cc3dd', ec='black')); ax.text(root_xy[0] + W / 2, root_xy[1] + H / 2, 'TKM root', ha='center', fontsize=8)
for k, v in place.items():
    ax.add_patch(Rectangle(v[:2], W, H, fc='#e8dcc0' if v[2] == 'R0' else '#d8c8a0', ec='black'))
    ax.text(v[0] + W / 2, v[1] + H / 2, 't%d %s' % (k, v[2]), ha='center', va='center', fontsize=8)
seq = [(root_xy[0] + W / 2, root_xy[1] + H / 2)] + [(place[k][0] + W / 2, place[k][1] + H / 2) for k in range(32)]
ax.plot([s[0] for s in seq], [s[1] for s in seq], color='#b63032', lw=1.2, marker='>', ms=3, label='chain order (down = ins/ovf; up reverse)')
ax.set_xlim(-30, PART[0] + 30); ax.set_ylim(-30, PART[1] + 30); ax.set_aspect('equal')
ax.set_title('root.u_tkm_SW chain snake (PATH-HBM)\n%s: worst hop %.1f um, %d bits > 405, obst %d, clr/conv bcast depth %d'
             % (audit['verdict'], worst, over, len(viol), bc_depth), fontsize=9)
ax.legend(loc='lower right', fontsize=7); fig.tight_layout(); fig.savefig(P / 'tkm_chain_plan.png', dpi=110)
