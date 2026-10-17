#!/usr/bin/env python3
"""Q-DV dv2r8f4 (Q-DIEPLAN3 blocker 10-17): dv2r8f3 with the W column re-planned in NATIVE orientations only
(the generator / ot_mts allow R0 / MX / MY / R180; licensed PHY abstracts have fixed pin faces).  Column width =
io_collective's native 4,157.976 um; the collective sits beside dvs_W5 (native 4,157.976 x 1,563.816, R0, E face to the
slice) so the AR stays at the backbone end; io_serdes x3 (native 2,320.056 x 1,563.57) and io_ucie are MY (FDI faces
E into the die, beachfront on the W die edge), stacked above / below the collective at x = 0; the control / D2D group
stays at the N end (native).  The arrays shift E by the column growth.  python3 build_dv2f4.py IN(dv2r8f3).json OUT.json"""
import json, sys
src, out = sys.argv[1:3]
d = json.load(open(src)); I = {i['n']: i for i in d['insts']}
G = 108.0
NAT = {'io_collective': (4157.976, 1563.816), 'io_serdes': (2320.056, 1563.57), 'io_serdes_1': (2320.056, 1563.57),
       'io_serdes_2': (2320.056, 1563.57)}
for n, (w, h) in NAT.items(): I[n]['w'], I[n]['h'] = w, h
ORI = {'io_collective': 'R0', 'io_serdes': 'MY', 'io_serdes_1': 'MY', 'io_serdes_2': 'MY', 'io_ucie': 'MY'}
COLBLK = set(NAT) | {'io_ucie', 'bump_pkg_s0', 'bump_pkg_s1', 'bump_die_ps', 'ucie_kv', 'd2d_rom', 'native59', 'sys_face',
                     'tt_ctlm', 'embed_prov', 'clk_rx', 'rstseq_rom', 'ckb_rom', 'rs_bump', 'bump_fwd_epoch', 'bump_fwd_lrst'}
arr0 = min(i['x'] for n, i in I.items() if n.startswith(('c16_', 'dvs_')))
lane = [n for n in I if n in ('dvl_a', 'dvl_b')]
CH = d.get('column_channel_um', 216.0)
newarr0 = round((NAT['io_collective'][0] + CH) / 8.64 + 0.4999) * 8.64       # keep the 8.64 cluster lattice
sh = newarr0 - arr0
for n, i in I.items():
    if n in COLBLK or n == 'die_margin_n': continue
    i['x'] = round(i['x'] + sh, 3)
for n in lane: I[n]['x'] = round(NAT['io_collective'][0] + CH / 2 - 5.4, 3)
sl = I['dvs_W5']; ym = sl['y'] + sl['h'] / 2
def put(n, x, y): I[n]['x'] = round(x, 3); I[n]['y'] = round(y, 3)
put('io_collective', 0.0, ym - NAT['io_collective'][1] / 2)
y = I['io_collective']['y'] + NAT['io_collective'][1] + G
for n in ('io_ucie', 'io_serdes'):
    put(n, 0.0, y); y += I[n]['h'] + G
top_io = y
y = I['io_collective']['y'] - G
for n in ('io_serdes_1', 'io_serdes_2'):
    y -= I[n]['h']; put(n, 0.0, y); y -= G
for k, n in enumerate(('bump_pkg_s0', 'bump_pkg_s1', 'bump_die_ps')):
    put(n, NAT['io_collective'][0] - 60 - 60 * k, I['io_collective']['y'] + NAT['io_collective'][1] + 30)
ctrl_bottom = min(I[n]['y'] for n in ('ucie_kv', 'd2d_rom', 'native59', 'sys_face', 'tt_ctlm', 'embed_prov', 'clk_rx', 'rstseq_rom'))
assert top_io <= ctrl_bottom, (top_io, ctrl_bottom)
for n, o in ORI.items(): I[n]['o'] = o
I['die_margin_n']['x'] = newarr0
d['insts'] = list(I.values()); d['column_um'] = newarr0; d['native_orientations'] = ORI
json.dump(d, open(out, 'w'))
W = max(i['x'] + i['w'] for i in I.values()) + 21.6; H = max(i['y'] + i['h'] for i in I.values()) + 21.6
print(out, 'column', round(newarr0, 2), 'die', round(W), 'x', round(H), round(W * H / 1e6, 1), 'mm2; io top', round(top_io), 'ctrl bottom', round(ctrl_bottom), 'serdes_2 bottom', round(I['io_serdes_2']['y']))
