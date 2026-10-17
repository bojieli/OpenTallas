#!/usr/bin/env python3
"""Q-DIEPLAN3 (2026-10-16): q3h array grid + homes for the C_B16 cluster contract (CB helper).

usage: mk_q3h_grid.py BASE_HOMES CONTRACT OUT_HOMES OUT_GRID [--head-gap 1179.36] [--band-gap 129.6] [--edge 129.6]

BASE = q3h-homes.json (A0 tiles 457.92 x 1166.4 + the VM/SU 43.2 channel). The contract's cluster outline (2350.08 x
5184: 4 columns at the cluster's own corridor pitch, 64.8 strips) is wider and taller than the A0 4 x 4 group, so the
arrays are re-pitched: 6 clusters per side abut horizontally; bands keep die channels (band gaps / die-edge channels:
the rs lanes) and a head gap tall enough for the 48 x-slice column heads (qfd_xcol in its w130 form 129.6 x 920.16, one
per die column at the column centre) plus a relay lane above and below them.  Tiles and corridor stations get homes
inside their cluster outline (contract geometry; they are retired by the q3h hook, their homes only keep the rebase
complete).  Centre column: rigid x shift (array growth) and y shift (head-gap centre); port stacks follow their band;
IO stays on the S edge; the KV stack follows the top edge.  OUT_GRID: the cluster origins / orientations, head sites,
channels and die outline (the q3h hook and the die-top tree read it).
"""
import argparse, json, re

ap = argparse.ArgumentParser()
ap.add_argument('base'); ap.add_argument('contract'); ap.add_argument('out'); ap.add_argument('grid')
ap.add_argument('--head-gap', type=float, default=1179.36)
ap.add_argument('--band-gap', type=float, default=129.6)
ap.add_argument('--edge', type=float, default=129.6)
ap.add_argument('--head-wh', default='129.6,920.16')
a = ap.parse_args()
B = json.load(open(a.base)); H = {k: dict(v) for k, v in B['homes'].items()}
C = json.load(open(a.contract))
CW, CH = C['outline_um']['w'], C['outline_um']['h']
cols_x = [C['geometry']['columns'][str(k)]['x'][0] for k in range(4)]
rows_y = [C['geometry']['rows'][str(k)]['y'][0] for k in range(4)]
TW, TH = 457.92, 1166.4
HW, HH = [float(z) for z in a.head_wh.split(',')]
S = 0.024
q = lambda z, g=0.216: round(round(z / g) * g, 3)

tiles = {n: h for n, h in H.items() if re.fullmatch(r't_\d+_\d+', n)}
old_row_y = sorted({h['y'] for h in tiles.values()})
assert len(old_row_y) == 16
old_band_y = [old_row_y[4 * b] for b in range(4)]
old_band_top = [old_row_y[4 * b + 3] + TH for b in range(4)]
old_hg = (old_band_top[1], old_band_y[2])
old_w = B['die']['w']; old_h = B['die']['h']
old_xw_right = max(h['x'] + TW for n, h in tiles.items() if int(n.split('_')[1]) < 24)
old_xe_left = min(h['x'] for n, h in tiles.items() if int(n.split('_')[1]) >= 24)
old_xe_right = max(h['x'] + TW for n, h in tiles.items() if int(n.split('_')[1]) >= 24)
x0 = min(h['x'] for h in tiles.values())

# ---- new grid
band_y = [q(x0 + a.edge)]
band_y.append(q(band_y[0] + CH + a.band_gap))
band_y.append(q(band_y[1] + CH + a.head_gap))
band_y.append(q(band_y[2] + CH + a.band_gap))
top = band_y[3] + CH
die_h = q(top + a.edge + x0)
hg = (band_y[1] + CH, band_y[2])
w_left = x0
w_right = w_left + 6 * CW
dW = q(w_right - old_xw_right, 0.432)
e_left = q(old_xe_left + dW, 0.432)
e_right = e_left + 6 * CW
die_w = q(e_right + (old_w - old_xe_right), 0.432)
dCore = q((hg[0] + hg[1]) / 2 - (old_hg[0] + old_hg[1]) / 2, 2.16)


def orient(side, band):
    return ('MX' if band <= 1 else 'R0') if side == 'W' else ('R180' if band <= 1 else 'MY')


clusters = []
for side in 'WE':
    for g in range(6):
        for band in range(4):
            x = (w_right - (g + 1) * CW) if side == 'W' else (e_left + g * CW)
            clusters.append(dict(n=f'c16_{side}{g}_{band}', side=side, g=g, band=band, x=round(x, 3), y=band_y[band],
                                 w=CW - S, h=CH - S, o=orient(side, band)))
cl = {(c['side'], c['g'], c['band']): c for c in clusters}


def local_to_die(c, lx, ly, w, h):
    o = c['o']
    X = (CW - lx - w) if o in ('MY', 'R180') else lx
    Y = (CH - ly - h) if o in ('MX', 'R180') else ly
    return round(c['x'] + X, 3), round(c['y'] + Y, 3)


heads = []
for n, h in list(H.items()):
    m_ = re.fullmatch(r't_(\d+)_(\d+)', n)
    if m_:
        c_, r = int(m_.group(1)), int(m_.group(2))
        side = 'W' if c_ < 24 else 'E'
        g = (23 - c_) // 4 if side == 'W' else (c_ - 24) // 4
        lc = c_ % 4 if side == 'W' else 3 - c_ % 4
        band, lr = r // 4, r % 4
        cc = cl[(side, g, band)]
        h['x'], h['y'] = local_to_die(cc, cols_x[lc], rows_y[lr], TW, TH)
        h['h'] = TH - S if abs(h['h'] - (TH - S)) < 0.1 else h['h']
for n, h in list(H.items()):
    m_ = re.fullmatch(r's_(\d+)_(\d+)', n)
    if m_:
        t = H[f't_{m_.group(1)}_{m_.group(2)}']
        h['x'] = q(t['x'] + TW + 6.048, 0.432)          # the corridor E of the tile (>= 64.8 wide in the contract)
        h['y'] = q(t['y'] + 400.0, 2.16)
    m_ = re.fullmatch(r'h_(\d+)', n)
    if m_:
        c_ = int(m_.group(1))
        t = H[f't_{c_}_0']
        h['w'], h['h'] = HW - S, HH - S
        h['x'] = q(t['x'] + TW / 2 - HW / 2, 0.432)
        h['y'] = q(hg[0] + (a.head_gap - HH) / 2, 2.16)
        heads.append(dict(n=n, x=h['x'], y=h['y'], w=h['w'], h=h['h']))
# centre column + port stacks + IO + KV
for n, h in H.items():
    if re.fullmatch(r'(t_\d+_\d+|s_\d+_\d+|h_\d+)', n):
        continue
    cy = h['y'] + h['h'] / 2
    if re.fullmatch(r'(io_\w+|bump_pkg_\w+|bump_die_\w+)', n):
        dy = 0.0
    elif re.fullmatch(r'(d2d_rom|ucie_kv|ckb_rom|rs_bump|bump_fwd_\w+)', n):
        dy = die_h - old_h
    elif re.fullmatch(r'(sp_port_tiles|sp_band_lanes|sp_res_ser)_\d(_f1)?', n):
        b = max([k for k in range(4) if cy >= old_band_y[k] - 1e-6] or [0])
        if b <= 1 and cy > old_band_top[1]:
            dy = dCore
        else:
            dy = band_y[b] - old_band_y[b]
    else:
        dy = dCore
    h['x'] = round(h['x'] + dW, 3)
    h['y'] = round(h['y'] + dy, 3)
# overlap / outside check
rects = sorted((h['x'], h['y'], h['x'] + h['w'], h['y'] + h['h'], n) for n, h in H.items())
bad = []
for i, (ax, ay, bx, by_, n) in enumerate(rects):
    for cx, cy, dx, dy, k in rects[i + 1:]:
        if cx >= bx - 1e-3:
            break
        if cy < by_ - 1e-3 and dy > ay + 1e-3:
            bad.append((n, k))
out = [n for x_, y_, u, w_, n in rects if x_ < -1e-3 or y_ < -1e-3 or u > die_w + 1e-3 or w_ > die_h + 1e-3]
O = dict(B)
O['die'] = dict(B['die'], w=die_w, h=die_h)
O['candidate'] = 'q3h_grid'
O['params'] = dict(B['params'], tile=[TW, TH], source='mk_q3h_grid.py', base_q3h=a.base, contract=a.contract,
                   cluster=[CW, CH], dW=dW, dCore=dCore, band_y=band_y, head_gap=list(hg),
                   sysface_xy=[round(B['params']['sysface_xy'][0] + dW, 3), round(B['params']['sysface_xy'][1] + dCore, 3)])
O['homes'] = H
json.dump(O, open(a.out, 'w'), indent=1)
G = dict(schema='opentallas.qwen.q3h.array_grid.v1', die=dict(w=die_w, h=die_h, mm2=round(die_w * die_h / 1e6, 3)),
         cluster=dict(master=C['master'], w=CW - S, h=CH - S), clusters=clusters, heads=heads,
         channels=dict(head_gap=list(hg), band_gaps=[[band_y[0] + CH, band_y[1]], [band_y[2] + CH, band_y[3]]],
                       bottom=[0, band_y[0]], top=[top, die_h]),
         shifts=dict(dW=dW, dCore=dCore), overlaps=bad[:20], outside=out[:20])
json.dump(G, open(a.grid, 'w'), indent=1)
print(f'die {die_w} x {die_h} = {die_w * die_h / 1e6:.2f} mm2 (was {old_w} x {old_h} = {old_w * old_h / 1e6:.2f}); dW {dW} dCore {dCore}; '
      f'head gap {hg}; overlaps {len(bad)} {bad[:6]}; outside {out[:6]}; sysface {O["params"]["sysface_xy"]}')
