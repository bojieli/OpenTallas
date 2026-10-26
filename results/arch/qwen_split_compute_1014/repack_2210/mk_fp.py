#!/usr/bin/env python3
"""Qwen compute die re-plan for the re-packed 64-lane tile (owner 20:35; held45 a2 slot 457.92 x 820.8).
usage: mk_fp.py NAME CORR SPINE_W MODE.  Topology kept (48 x 16 columns/rows, corridor stations, xcol heads, spine hub).
  column pitch = 457.92 + CORR (head hop xcol w_d -> next e_d = pitch - 64.78 must stay <= 500 um)
  row pitch 864 (gap 43.2); head gap so xcol fits between s_c_7 and s_c_8 (y8 - y7 = 1555.2)
  station y = tile y + 410.4 (tile tap 437.2..485.87 vs station tap_d 27.46..76.13)
  MODE r1: port_tiles_b on the W spine edge / _f1 on the E edge beside the VM/SU cluster (port<->f1 crosses the cluster)
       r2: two-column spine, s6 band stacks [port | 522.72 | f1] at their rows in the W column, cluster in the E column
       r3: the three band stacks side by side at the spine bottom, cluster above
Tile master pins from the a2 kit plan (die-granted)."""
import json, sys
from pathlib import Path
G0 = '/home/ubuntu/artifacts/globalfp/qwen/structural-1417/upper-specialized-routing-capacity-source.json'
S6 = '/home/ubuntu/artifacts/globalfp/qwen/fpq-1705/fpq_s6-homes.json'
OUT = Path('/home/ubuntu/artifacts/globalfp/qwen/fpq-2210')
name, CORR, WS, MODE = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
ROWGAP = float(sys.argv[5]) if len(sys.argv) > 5 else 43.2
TW, TH = 457.92, 820.8
PC = TW + CORR; PR = TH + ROWGAP; HEADGAP = 1555.2 - 864.0; STY = 410.4
PT = (1036.8, 2462.4)
g = json.load(open(G0)); h6 = json.load(open(S6))['homes']
snap = lambda v, q=2.16: round(round(v / q) * q, 3)
ranges = {'n_a': (61.66, 160.96), 'n_b': (162.26, 261.56), 't_out': (262.76, 362.06), 'n_y': (363.26, 462.56),
          'tie_lo': (429.2, 430.2), 'tie_hi': (430.7, 431.7), 'tile_id': (432.2, 435.2), 'rst_n': (435.7, 436.7), 'tap': (437.2, 485.872)}
face = {k: ('W' if k in ('n_a', 'n_b', 't_out', 'n_y') else 'E') for k in ranges}
for mn in ('qfd_tile_nk', 'qfd_tile_nl'):
    M = g['masters'][mn]; by = {}
    for p in M['pins']:
        by.setdefault(p['name'].split('[')[0], []).append(p)
    pins = []
    for base, ps in by.items():
        if base in ranges:
            lo, hi = ranges[base]; n = len(ps)
            for k, p in enumerate(sorted(ps, key=lambda q: int(q['name'].split('[')[1][:-1]) if '[' in q['name'] else 0)):
                y = round(lo + (hi - lo) * k / max(1, n - 1), 3); x0 = 0.0 if face[base] == 'W' else TW - 0.192
                pins.append(dict(name=p['name'], layer='M4', rect=[x0, y - .012, x0 + .192, y + .012]))
        else:
            for p in ps:
                r = p['rect']; sx, sy = TW / M['w'], TH / M['h']
                pins.append(dict(name=p['name'], layer=p['layer'], rect=[round(r[0]*sx, 3), round(r[1]*sy, 3), round(r[0]*sx, 3) + r[2]-r[0], round(r[1]*sy, 3) + r[3]-r[1]]))
    M.update(w=TW, h=TH, pins=pins)
X0, Y0 = (float(sys.argv[6]) if len(sys.argv) > 6 else 86.4), 1641.6
rowy = lambda r: Y0 + r * PR + (HEADGAP + 864.0 - PR if r >= 8 else 0.0) if False else Y0 + r * PR + (max(HEADGAP, 1555.2 - PR) if r >= 8 else 0.0)
I = {i['n']: i for i in g['insts']}; homes = {}
def put(n, x, y, o=None):
    i = I[n]; m = g['masters'][i['m']]
    homes[n] = dict(m=i['m'], x=round(x, 3), y=round(y, 3), o=o or h6[n]['o'], w=m['w'], h=m['h'])
XS0 = X0 + 24 * PC; XE0 = XS0 + WS + CORR
for c in range(48):
    xc = X0 + c * PC if c < 24 else XE0 + (c - 24) * PC
    for r in range(16):
        put(f't_{c}_{r}', xc, rowy(r), 'R0'); put(f's_{c}_{r}', xc + TW, rowy(r) + STY, 'R0')
    put(f'h_{c}', xc + TW, snap(rowy(7) + STY + 103.656 + 4.32), 'R0')
cluster = ['sp_vector_memory', 'sp_su64_sfu', 'seq_su', 'xs_tap', 'clk_rx', 'up4_sel_station', 'res_train_issue', 'tt_ctlm',
           'native59', 'embed_prov'] + [f'cbuf_g_{k}' for k in range(8)] + [f'crom_g_{k}' for k in range(8)]
bx0 = min(h6[n]['x'] for n in cluster); bx1 = max(h6[n]['x'] + h6[n]['w'] for n in cluster)
by0 = min(h6[n]['y'] for n in cluster); by1 = max(h6[n]['y'] + h6[n]['h'] for n in cluster)
cw, ch = bx1 - bx0, by1 - by0
vm = h6['sp_vector_memory']
SW = 2 * PT[0] + 522.72      # one s6 band stack width
cx = XS0 + (WS - cw) / 2.0
cy = rowy(8) - (vm['y'] + vm['h'] - by0)
if MODE == 'r2':
    cx = XS0 + WS - float(__import__('os').environ.get('CLU_E', '21.6')) - cw
if MODE == 'r3':
    cy = Y0 + 518.4 + 43.2 + PT[1] + 43.2 + 1131.84 + 129.6
dx, dy = snap(cx - bx0, 8.64), snap(cy - by0, 8.64)
for n in cluster:
    put(n, h6[n]['x'] + dx, h6[n]['y'] + dy)
CY0, CY1 = by0 + dy, by1 + dy
band_mid = lambda b: (rowy(2 + 4 * b) + rowy(5 + 4 * b) + TH) / 2.0
def stack(b, x, y):
    o = h6[f'sp_port_tiles_{b}']['o']
    lo, hi = (f'sp_res_ser_{b}', 518.4), (f'sp_band_lanes_{b}', 1131.84)
    if o == 'R0':
        lo, hi = hi, lo
    put(lo[0], x + 129.6, y)
    yp = y + lo[1] + 43.2
    put(f'sp_port_tiles_{b}', x, yp); put(f'sp_port_tiles_{b}_f1', x + PT[0] + 522.72, yp)
    put(hi[0], x + 129.6, yp + PT[1] + 43.2)
    return yp + PT[1] + 43.2 + hi[1]
if MODE == 'r1':
    for b in range(3):
        yp = snap(band_mid(b) - PT[1] / 2, 8.64)
        put(f'sp_port_tiles_{b}', XS0 + 21.6, yp, 'R0'); put(f'sp_port_tiles_{b}_f1', XS0 + WS - 21.6 - PT[0], yp, 'R0')
    def strip(b, y):
        put(f'sp_band_lanes_{b}', XS0 + 21.6 + PT[0] + 216.0, y, 'R0')
        put(f'sp_res_ser_{b}', XS0 + 21.6 + PT[0] + 216.0 + 881.28 + 216.0, y, 'R0')
    strip(0, snap(CY0 - 216.0 - 1131.84, 8.64)); strip(2, snap(CY1 + 216.0, 8.64))
    strip(1, snap(CY0 - 216.0 - 1131.84 - 216 - 1131.84, 8.64))
    upx, upy = homes['sp_res_ser_1']['x'] + 777.6 + 108.0, homes['sp_band_lanes_1']['y']
elif MODE == 'r2':
    y = Y0
    for b in range(3):
        y = snap(stack(b, XS0 + 21.6, snap(max(y + 86.4, band_mid(b) - 2100), 8.64)), 8.64)
    upx, upy = XS0 + 21.6 + PT[0] + 21.6, homes['sp_band_lanes_0']['y'] + 1200
else:
    for b in range(3):
        stack(b, XS0 + 21.6 + b * (SW + 86.4), Y0)
    upx, upy = XS0 + 21.6 + 3 * (SW + 86.4), Y0
for k, n in enumerate(['tt_up4_leaf0', 'tt_up4_leaf1', 'tt_up4_leaf2', 'tt_up4_leaf3']):
    put(n, upx + k * 86.4, upy)
put('up4_sel_branch0', upx, upy + 259.2); put('up4_sel_branch1', upx + 43.2, upy + 259.2); put('rstseq_rom', upx, upy + 345.6)
io = ['io_collective', 'io_ucie', 'io_serdes', 'io_serdes_1', 'io_serdes_2']
ix0 = min(h6[n]['x'] for n in io); ix1 = max(h6[n]['x'] + h6[n]['w'] for n in io)
idx = snap(XS0 + WS / 2 - (ix0 + ix1) / 2, 8.64)
for n in io:
    put(n, h6[n]['x'] + idx, h6[n]['y'])
top = ['d2d_rom', 'ucie_kv', 'rs_bump', 'ckb_rom', 'bump_fwd_epoch', 'bump_fwd_lrst']
DH = max([rowy(15) + TH] + [v['y'] + v['h'] for v in homes.values()]) + 21.6
ty1 = max(h6[n]['y'] + h6[n]['h'] for n in top); tx = snap(XS0 + WS - 1300 - min(h6[n]['x'] for n in top), 8.64)
for n in top:
    put(n, h6[n]['x'] + tx, h6[n]['y'] - ty1 + DH - 21.6)
assert set(I) == set(homes), set(I) - set(homes)
DW = snap(XE0 + 24 * PC + 21.6, 8.64); DH = snap(max(v['y'] + v['h'] for v in homes.values()) + 30, 8.64)
L = sorted(homes.items(), key=lambda kv: kv[1]['x']); ov = []
for a in range(len(L)):
    na, A = L[a]
    for b in range(a + 1, len(L)):
        nb, B = L[b]
        if B['x'] >= A['x'] + A['w'] - 1e-6: break
        if min(A['y'] + A['h'], B['y'] + B['h']) - max(A['y'], B['y']) > 1e-6: ov.append((na, nb))
out_ = [n for n, v in homes.items() if v['x'] < 0 or v['y'] < 0 or v['x'] + v['w'] > DW + 1e-6 or v['y'] + v['h'] > DH + 1e-6]
g['die'].update(w=DW, h=DH, mm2=round(DW * DH / 1e6, 3))
for i in g['insts']:
    i.update({k: homes[i['n']][k] for k in ('x', 'y', 'w', 'h')}, o=homes[i['n']]['o'])
json.dump(g, open(OUT / f'{name}-graph.json', 'w'))
json.dump(dict(schema='opentallas.qwen.globalfp-q-homes.2210.v1', candidate=name, homes=homes, reserve={}, die=dict(w=DW, h=DH),
               params=dict(corridor=CORR, spine=WS, mode=MODE, row_pitch=PR, headgap=HEADGAP, tile=[TW, TH])), open(OUT / f'{name}-homes.json', 'w'), indent=0)
print(name, MODE, 'die', DW, DH, round(DW * DH / 1e6, 1), 'mm2 overlaps', len(ov), ov[:6], 'outside', out_[:6])
