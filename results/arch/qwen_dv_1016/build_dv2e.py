#!/usr/bin/env python3
"""Q-DV dv2r8e (owner via coordinator 10-17): SerDes / IO beachfront on the W / E die edges beside the end slices
dvs_W5 / dvs_E5 (the ends of the stream backbone); centre closed to the minimum channel for the W<->E stream lane,
tt_ctlm and the N-edge D2D group (ucie_kv stays on the N edge: KV die abuts there; package-legal, nearest the centre).
Transform of dv2r8.json.  Variants:
  A  all IO (io_collective + 3 io_serdes + io_ucie) in ONE W-edge column (rotated 90), centred on the slice row
  B  io_collective (digital, no beachfront) in the centre column; io_serdes_2 + io_serdes_1 on the W edge,
     io_serdes + io_ucie on the E edge (FDI links run along the slice row to the centre)
    python3 build_dv2e.py IN.json OUT.json A|B"""
import json, sys
src, out, var = sys.argv[1:4]
d = json.load(open(src)); I = {i['n']: i for i in d['insts']}
G = 108.0
xw1 = I['c16_W0_1']['x'] + I['c16_W0_1']['w']; xe0 = I['c16_E0_1']['x']
sl = I['dvs_W0']; ym = sl['y'] + sl['h'] / 2
IO = ['io_collective', 'io_serdes', 'io_serdes_1', 'io_serdes_2', 'io_ucie']
for n in IO:                                         # rotate 90: long side vertical along the edge
    I[n]['w'], I[n]['h'] = I[n]['h'], I[n]['w']
centre = ['tt_ctlm', 'native59', 'd2d_rom', 'ucie_kv', 'sys_face', 'embed_prov', 'rstseq_rom', 'clk_rx', 'ckb_rom', 'rs_bump',
          'bump_fwd_epoch', 'bump_fwd_lrst', 'bump_pkg_s0', 'bump_pkg_s1', 'bump_die_ps', 'dvx_w', 'dvx_e', 'dva_W', 'dva_E', 'dvk_W', 'dvk_E']
if var == 'B': centre.append('io_collective')
CW = max(I[n]['w'] for n in centre if n in I) + 2 * G      # centre channel = widest centre block + 2 channels
west_io = ['io_serdes_2', 'io_serdes_1', 'io_collective', 'io_ucie', 'io_serdes'] if var == 'A' else ['io_serdes_2', 'io_serdes_1']
east_io = [] if var == 'A' else ['io_serdes', 'io_ucie']
WW = (max(I[n]['w'] for n in west_io) + G) if west_io else 0
EW = (max(I[n]['w'] for n in east_io) + G) if east_io else 0
shift_w = WW; new_xe0 = xw1 + WW + CW; shift_e = new_xe0 - xe0
for n, i in I.items():
    if n in IO or n in centre: continue
    cx = i['x'] + i['w'] / 2
    i['x'] = round(i['x'] + (shift_w if cx < (xw1 + xe0) / 2 else shift_e), 3)
cx0 = xw1 + WW + CW / 2                             # centre column axis
def stack(names, x, yc):
    h = sum(I[n]['h'] for n in names) + G * (len(names) - 1); y = yc - h / 2
    for n in names:
        I[n]['x'] = round(x, 3); I[n]['y'] = round(y, 3); y += I[n]['h'] + G
def edge_x(n, side, W_):                            # flush to the die edge
    return 0.0 if side == 'W' else W_ - I[n]['w']
# centre: D2D group at the N edge (unchanged order top-down), tt_ctlm on the slice row, clock / reset / embed below it
H = max(i['y'] + i['h'] for i in I.values())
I['ucie_kv']['x'] = round(cx0 - I['ucie_kv']['w'] / 2, 3)
for n in ('ckb_rom', 'rs_bump', 'bump_fwd_epoch', 'bump_fwd_lrst'):
    I[n]['x'] = round(I['ucie_kv']['x'] - 60, 3)
I['d2d_rom']['x'] = round(cx0 - I['d2d_rom']['w'] / 2, 3); I['d2d_rom']['y'] = round(I['ucie_kv']['y'] - 4.32 - I['d2d_rom']['h'], 3)
I['native59']['x'] = round(cx0 - I['native59']['w'] / 2, 3); I['native59']['y'] = round(I['d2d_rom']['y'] - G - I['native59']['h'], 3)
I['sys_face']['x'] = round(cx0 - I['sys_face']['w'] / 2, 3); I['sys_face']['y'] = round(I['native59']['y'] - G - I['sys_face']['h'], 3)
I['tt_ctlm']['x'] = round(cx0 - I['tt_ctlm']['w'] / 2, 3); I['tt_ctlm']['y'] = round(ym - I['tt_ctlm']['h'] / 2, 3)
for k, n in enumerate(('embed_prov', 'clk_rx', 'rstseq_rom')):
    I[n]['x'] = round(cx0 - I[n]['w'] / 2, 3); I[n]['y'] = round(I['tt_ctlm']['y'] - (k + 1) * 600 - I[n]['h'], 3)
for n in ('dvx_w', 'dvx_e'):
    I[n]['x'] = round(xw1 + WW + (20 if n == 'dvx_w' else CW - 30), 3)
if var == 'B':
    I['io_collective']['x'] = round(cx0 - I['io_collective']['w'] / 2, 3); I['io_collective']['y'] = round(I['clk_rx']['y'] - 2200 - I['io_collective']['h'], 3)
Wd = new_xe0 + (xe0 - xw1) * 0 + (max(i['x'] + i['w'] for n, i in I.items() if n not in IO and n not in centre) - new_xe0) + EW
stack(west_io, 0.0, ym)
for n in east_io: I[n]['x'] = 0
stack(east_io, 0.0, ym)
for n in east_io: I[n]['x'] = round(Wd - I[n]['w'], 3)
for k, n in enumerate(('bump_pkg_s0', 'bump_pkg_s1', 'bump_die_ps')):   # rank straps: only io_collective reads them
    I[n]['x'] = round(I['io_collective']['x'] + I['io_collective']['w'] + 30, 3); I[n]['y'] = round(I['io_collective']['y'] + 100 + 100 * k, 3)
# AR / D2D edge lanes: AR now from the END slices to the edge IO (A: W5 only; B: g0 -> centre collective)
B2 = []
for b, c, bits, eps in d['buses']:
    if b.startswith(('dv_ar_', 'dv_ar2_')): continue
    B2.append([b, c, bits, eps])
if var == 'A':
    B2.append(['dv_ar_W', 'dv_coll', 2 * 1064, ['dvs_W5', 'io_collective']])     # whole-die AR enters at the W end
else:
    for s in 'WE':
        B2.append([f'dv_ar_{s}', 'dv_coll', 1064, [f'dvs_{s}0', f'dva_{s}']]); B2.append([f'dv_ar2_{s}', 'dv_coll', 1064, [f'dva_{s}', 'io_collective']])
        I[f'dva_{s}']['x'] = round(cx0 + (-200 if s == 'W' else 200), 3); I[f'dva_{s}']['y'] = round(I['io_collective']['y'] + I['io_collective']['h'] + G, 3)
for s in 'WE':
    I[f'dvk_{s}']['x'] = round(cx0 + (-300 if s == 'W' else 300), 3)
d['insts'] = list(I.values()); d['buses'] = B2; d['variant'] = var; d['centre_um'] = CW
json.dump(d, open(out, 'w'))
print(out, var, 'centre', round(CW), 'W io col', round(WW), 'E io col', round(EW), 'die W', round(Wd + 21.6))
