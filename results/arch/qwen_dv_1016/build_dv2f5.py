#!/usr/bin/env python3
"""Q-DV dv2r8f5 (coordinator decision 10-17 + Q-DIEPLAN3 smoke): from dv2r8f3
  * W-column IO as NEW native masters, not rotations: modeled E/W-edge PHY abstract variants
    ot_qfd_serdes_112g_x12_phy_s597_ew (1,563.57 x 2,320.056, bump face on the W die edge, FDI on the E face) and the
    re-kitted narrow collective qfd_collective_static_io_production_ns (1,563.816 x 4,157.976; our RTL, not closed ->
    re-kit by Q-COLL); io_ucie native square (MY)
  * slices ABUT the band-1 / band-2 cluster faces (the 129.6-um lanes above / below the slice row removed, the upper
    half moved down 259.2 = 30 lattice steps): the 2,064-b corridor words + 1,028-b rs per slice cross face to face on
    aligned pins (as the q3h VM/SU seam rule), not through a die channel -- Q-DIEPLAN3 measured 0.564 there with the
    real corridor pin ranges.  python3 build_dv2f5.py IN(dv2r8f3).json OUT.json"""
import json, sys
src, out = sys.argv[1:3]
d = json.load(open(src)); I = {i['n']: i for i in d['insts']}
REN = {'io_serdes': 'ot_qfd_serdes_112g_x12_phy_s597_ew', 'io_serdes_1': 'ot_qfd_serdes_112g_x12_phy_s597_ew',
       'io_serdes_2': 'ot_qfd_serdes_112g_x12_phy_s597_ew', 'io_collective': 'qfd_collective_static_io_production_ns'}
for n, m in REN.items(): I[n]['m'] = m
b1 = I['c16_W0_1']; b2 = I['c16_W0_2']
gap_lo = b1['y'] + b1['h']; sl = I['dvs_W0']
lane_lo = sl['y'] - gap_lo; lane_hi = b2['y'] - (sl['y'] + sl['h'])
dy = int((lane_lo + lane_hi) / 8.64) * 8.64          # keep band 2-3 cluster origins on the 8.64 lattice
newb2 = b2['y'] - dy
for n, i in I.items():
    if n.startswith('dvs_'): i['y'] = round(gap_lo, 3); i['h'] = round(newb2 - gap_lo, 3)   # abut both faces
    elif i['y'] >= b2['y'] - 1e-6: i['y'] = round(i['y'] - dy, 3)
    elif i['y'] > sl['y'] + sl['h'] - 1e-6 and not n.startswith('c16_'): i['y'] = round(i['y'] - lane_lo, 3)
# re-stack the W-column IO contiguously around the slice row (collective centred on dvs_W5)
G = 108.0; sl5 = I['dvs_W5']; ym = sl5['y'] + sl5['h'] / 2
co = I['io_collective']; co['y'] = round(ym - co['h'] / 2, 3)
y = co['y'] + co['h'] + G
for n in ('io_ucie', 'io_serdes'):
    I[n]['y'] = round(y, 3); y += I[n]['h'] + G
y = co['y'] - G
for n in ('io_serdes_1', 'io_serdes_2'):
    y -= I[n]['h']; I[n]['y'] = round(y, 3); y -= G
for k, n in enumerate(('bump_pkg_s0', 'bump_pkg_s1', 'bump_die_ps')):
    I[n]['y'] = round(co['y'] + 100 + 100 * k, 3)
d['insts'] = list(I.values()); d['slice_abut'] = True
json.dump(d, open(out, 'w'))
W = max(i['x'] + i['w'] for i in I.values()) + 21.6; H = max(i['y'] + i['h'] for i in I.values()) + 21.6
print(out, 'lanes removed', lane_lo, lane_hi, 'die', round(W), 'x', round(H), round(W * H / 1e6, 1), 'mm2')
