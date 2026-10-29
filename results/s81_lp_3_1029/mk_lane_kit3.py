import re, sys
from pathlib import Path
R = Path(sys.argv[1])
s = (R / 'results/s81_lp_2_1029/lane_kit.py').read_text()
rep = [
 ('"""S81-LP-2 (2026-10-29): compact', '"""S81-LP-3 (2026-10-29) TIGHT variant T (GEOM-56 06:47: A fill_of_free < 0.15 predicted, B aspect 2.086 > 2.0; tight option ~283x490) of the S81-LP-2 lane_kit.py generator, derived by mk_lane_kit3.py: one 6-column lattice with 10.99-um channels and one 13.37-um middle channel (centre clock-entry island + 4.32 halos), group gaps 11.016, big-row pitch 52.272, N band 40.\nOriginal S81-LP-2 doc: compact'),
 ("VAR = {'A': dict(w=345.6, h=561.6, per_big=6, per_small=6, big_pitch=(55.296, 56.16), small_pitch=(55.296, 25.92)),",
  "VAR = {'T': dict(w=295.92, h=473.04, per_big=6, per_small=6, big_pitch=(45.576, 52.272), small_pitch=(45.576, 25.92),\n                 col_dx=[0, 45.576, 91.152, 139.104, 184.68, 230.256], gap=11.016, edge=10.8, chan=10.8)}\n_UNUSED = {'A': dict(w=345.6, h=561.6, per_big=6, per_small=6, big_pitch=(55.296, 56.16), small_pitch=(55.296, 25.92)),"),
 ("        span = (per - 1) * px + SZ[BG][0]   # column lattice = big-macro width",
  "        cdx = p.get('col_dx') or [c_ * px for c_ in range(per)]\n        span = cdx[per - 1] + SZ[BG][0]   # column lattice = big-macro width"),
 ("        assert x0 - 4.32 >= 12.0 and w - 4.32 - (x0 + span) >= 12.0 and px - SZ[BG][0] >= 12.0, (v, x0, span)",
  "        E_, C_ = p.get('edge', 12.0), p.get('chan', 12.0)\n        assert x0 - 4.32 >= E_ and w - 4.32 - (x0 + span) >= E_ and min(b_ - a_ for a_, b_ in zip(cdx, cdx[1:])) - SZ[BG][0] >= C_, (v, x0, span)"),
 ("at=[round(x0 + c * px, 3), round(y + r * py, 3)]", "at=[round(x0 + cdx[c], 3), round(y + r * py, 3)]"),
 ("        y = y + (nrow - 1) * py + mh + 12.96", "        y = y + (nrow - 1) * py + mh + p.get('gap', 12.96)"),
 ("s['name'] = f'dscoll_lane_w_lp2{v.lower()}'", "s['name'] = f'dscoll_lane_w_lp3{v.lower()}'"),
 ("(f'S81-LP-2 compact LP hard child variant", "(f'S81-LP-3 tight LP hard child variant"),
 ("typ = f'source_coll_lane_w_lp2{v.lower()}'", "typ = f'source_coll_lane_w_lp3{v.lower()}'"),
 ("suffix=f'lp2{v.lower()}'", "suffix=f'lp3{v.lower()}'"),
]
for a, b in rep:
    assert s.count(a) == 1, a
    s = s.replace(a, b)
(R / 'results/s81_lp_3_1029/lane_kit3.py').write_text(s)
