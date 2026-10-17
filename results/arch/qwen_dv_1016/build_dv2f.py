#!/usr/bin/env python3
"""Q-DV dv2r8f (owner 10-17, no empty regions): from dv2r8e
  * centre closed to CW (default 0): the W and E arrays and slice rows abut; dvs_W0 | dvs_E0 exchange the stream face to
    face (as every slice pair does); no die net needs a centre channel any more (the D2D / control group moves out)
  * the control / D2D group goes to the N end of the W-edge column, packed two abreast (778-um blocks in the 1,672-um
    column): ucie_kv on the N edge at the W corner (KV die abuts the N edge, shifted to the W corner: same edge as today),
    d2d_rom under it (FDI abutted), native59 | sys_face, tt_ctlm | embed / clk_rx / rstseq
  * the PHY stack (serdes_2, serdes_1, collective, io_ucie, serdes) stays contiguous, centred on the slice row
    python3 build_dv2f.py IN(dv2r8e).json OUT.json [CW]"""
import json, sys
src, out = sys.argv[1:3]; CW = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
d = json.load(open(src)); I = {i['n']: i for i in d['insts']}
G = 108.0
xw1 = I['c16_W0_1']['x'] + I['c16_W0_1']['w']; xe0 = I['c16_E0_1']['x']
dx = (xe0 - xw1) - CW
IO = {'io_collective', 'io_serdes', 'io_serdes_1', 'io_serdes_2', 'io_ucie', 'bump_pkg_s0', 'bump_pkg_s1', 'bump_die_ps'}
CTRL = ['ucie_kv', 'd2d_rom', 'native59', 'sys_face', 'tt_ctlm', 'embed_prov', 'clk_rx', 'rstseq_rom', 'ckb_rom', 'rs_bump', 'bump_fwd_epoch', 'bump_fwd_lrst']
for n, i in I.items():
    if n in IO or n in CTRL: continue
    if i['x'] + i['w'] / 2 > (xw1 + xe0) / 2: i['x'] = round(i['x'] - dx, 3)
colw = max(I[n]['x'] + I[n]['w'] for n in IO if n.startswith('io_'))
H = max(i['y'] + i['h'] for n, i in I.items() if n.startswith('c16_'))
top = H
def put(n, x, y): I[n]['x'] = round(x, 3); I[n]['y'] = round(y, 3)
# N end of the column: ucie_kv on the N edge, d2d abutted below (FDI 4.32 um), bumps beside
put('ucie_kv', 0.0, top - I['ucie_kv']['h']); put('d2d_rom', 0.0, I['ucie_kv']['y'] - 4.32 - I['d2d_rom']['h'])
for k, n in enumerate(('ckb_rom', 'rs_bump', 'bump_fwd_epoch', 'bump_fwd_lrst')):
    put(n, I['ucie_kv']['w'] + 30 + 60 * k, top - 60)
put('native59', 0.0, I['d2d_rom']['y'] - G - I['native59']['h'])
put('sys_face', I['ucie_kv']['w'] + G, I['native59']['y'] + I['native59']['h'] - I['sys_face']['h'])
put('tt_ctlm', 0.0, I['native59']['y'] - G - I['tt_ctlm']['h'])
x2 = I['tt_ctlm']['w'] + G; y = I['tt_ctlm']['y'] + I['tt_ctlm']['h']
for n in ('embed_prov', 'clk_rx', 'rstseq_rom'):
    y -= I[n]['h']; put(n, x2, y); y -= G
ctrl_bottom = min(I[n]['y'] for n in CTRL)
# lane relays: crossing lane gone (abutted); edge lanes now along the column
for n in ('dvx_w', 'dvx_e'):
    I.pop(n, None)
d['buses'] = [b for b in d['buses'] if b[0] not in ('dv_x0', 'dv_x1', 'dv_x2')]
d['buses'].append(['dv_x0', 'dv_gather', 2 * 1088 + 96, ['dvs_W0', 'dvs_E0']])
# D2D / ib: from the column (native59, tt_ctlm) along the slice-row lane to W5 (the backbone end); E side via the backbone
d['buses'] = [b for b in d['buses'] if not b[0].startswith(('dv_kv', 'dv_ib_'))]
for n in ('dvk_W', 'dvk_E'): I.pop(n, None)
d['buses'] += [['dv_kv_W', 'dv_d2d', 2 * 1068, ['dvs_W5', 'native59']], ['dv_ib_W', 'tree_spine', 380, ['tt_ctlm', 'dvs_W5']]]
# column channel: widen the PHY-column / array channel to CH so the D2D + ib lanes (2,516 b) run inside it, not over W5
CH = float(sys.argv[4]) if len(sys.argv) > 4 else 216.0
colx = max(I[n]['x'] + I[n]['w'] for n in CTRL + [k for k in IO if k.startswith('io_')])
arr0 = min(i['x'] for n, i in I.items() if n.startswith(('c16_', 'dvs_')))
sh = colx + CH - arr0
for n, i in I.items():
    if n in IO or n in CTRL: continue
    i['x'] = round(i['x'] + sh, 3)
lx = colx + CH / 2 - 5.4; sl = I['dvs_W5']
for n, y in (('dvl_a', I['native59']['y']), ('dvl_b', sl['y'] + sl['h'] - 300)):   # lane enters W5 near its N-W corner
    I[n] = dict(n=n, m='qfd_dv_lane_relay', x=round(lx, 3), y=round(y, 3), w=10.8, h=10.8)
d['buses'] = [b for b in d['buses'] if b[0] not in ('dv_kv_W', 'dv_ib_W')]
d['buses'] += [['dv_kv_W', 'dv_d2d', 2 * 1068, ['native59', 'dvl_a']], ['dv_kv_W2', 'dv_d2d', 2 * 1068, ['dvl_a', 'dvl_b']],
               ['dv_kv_W3', 'dv_d2d', 2 * 1068, ['dvl_b', 'dvs_W5']], ['dv_ib_W', 'tree_spine', 380, ['tt_ctlm', 'dvl_a']]]
d['insts'] = list(I.values()); d['centre_um'] = CW; d['column_channel_um'] = CH
json.dump(d, open(out, 'w'))
phy_top = max(I[n]['y'] + I[n]['h'] for n in IO if n.startswith('io_'))
print(out, 'centre', CW, 'column', round(colw), 'ctrl group y', round(ctrl_bottom), '..', round(top), 'PHY stack top', round(phy_top), 'gap', round(ctrl_bottom - phy_top))
