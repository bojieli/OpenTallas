#!/usr/bin/env python3
"""Q-DV dv2r8g (coordinator risk follow-up 10-17): from dv2r8f, the D2D / KV-link group (ucie_kv on the W edge,
d2d_rom abutted, native59, sys_face) and tt_ctlm / embed / clk_rx / rstseq move into the W IO column at slice-row
height next to io_collective; PHYs above and below.  PACKAGE-CONDITIONAL: needs the KV die on the W edge at the
slice-row height (short side on, rotated), which the KV die / package owners must approve.
    python3 build_dv2g.py IN(dv2r8f).json OUT.json"""
import json, sys
src, out = sys.argv[1:3]
d = json.load(open(src)); I = {i['n']: i for i in d['insts']}
G = 108.0
sl = I['dvs_W5']; ys0, ys1 = sl['y'], sl['y'] + sl['h']; ym = (ys0 + ys1) / 2
def put(n, x, y): I[n]['x'] = round(x, 3); I[n]['y'] = round(y, 3)
# PHYs from the N end down (no FDI crosses another block): io_serdes_2, io_serdes_1, io_serdes, io_ucie, then the
# collective (overlapping the slice row), then the D2D group under it (native59 row facing W5): every FDI and the
# D2D / ib links stay in their own column span
H = max(i['y'] + i['h'] for n, i in I.items() if n.startswith('c16_'))
y = H
for n in ('io_serdes_2', 'io_serdes_1', 'io_serdes', 'io_ucie'):
    y -= I[n]['h']; put(n, 0.0, y); y -= G
y -= I['io_collective']['h'] - G; y -= G; put('io_collective', 0.0, y)
for k, n in enumerate(('bump_pkg_s0', 'bump_pkg_s1', 'bump_die_ps')):
    put(n, I['io_collective']['w'] - 60, y + 100 + 100 * k)
y -= G
y -= I['native59']['h']; put('native59', 0.0, y); put('sys_face', I['native59']['w'] + G, y); y -= G
y -= I['ucie_kv']['h']; put('ucie_kv', 0.0, y); put('d2d_rom', I['ucie_kv']['w'] + 4.32, y + I['ucie_kv']['h'] - I['d2d_rom']['h'])
for k, n in enumerate(('ckb_rom', 'rs_bump', 'bump_fwd_epoch', 'bump_fwd_lrst')):
    put(n, I['d2d_rom']['x'] + 20 + 60 * k, y + 60)
y -= G; y -= I['tt_ctlm']['h']; put('tt_ctlm', 0.0, y); yy = y + I['tt_ctlm']['h']
for n in ('embed_prov', 'clk_rx', 'rstseq_rom'):
    yy -= I[n]['h']; put(n, I['tt_ctlm']['w'] + G, yy); yy -= G
grp_bottom = y
for n in ('dvl_a', 'dvl_b'): I.pop(n, None)
d['buses'] = [b for b in d['buses'] if b[0] not in ('dv_kv_W', 'dv_kv_W2', 'dv_kv_W3', 'dv_ib_W')]
d['buses'] += [['dv_kv_W', 'dv_d2d', 2 * 1068, ['dvs_W5', 'native59']], ['dv_ib_W', 'tree_spine', 380, ['tt_ctlm', 'dvs_W5']]]
d['insts'] = list(I.values()); d['package_conditional'] = 'KV die on the W edge at slice-row height'
json.dump(d, open(out, 'w'))
print(out, 'collective', round(I['io_collective']['y']), '..', round(I['io_collective']['y'] + I['io_collective']['h']), 'slice row', round(ys0), '..', round(ys1), 'D2D group bottom', round(grp_bottom))
