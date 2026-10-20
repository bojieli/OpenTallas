#!/usr/bin/env python3
"""KV-ATTN5 10-20 (tree K.STA.AHUB): qkd_ahub_g7c = qkd_ahub_g7a source, RE-FLOORPLANNED with more channel area.

g6a/g6b (and g7a, same geometry) sit in GRT extra iterations for hours (g4b: 49 iterations, 353 overflow at 15 % total
usage = local hot spots, M5/M4 worst), so g7c widens every std-cell region instead of squeezing:
  outline 734.4 x 540 -> 820.8 x 626.4 (+29 % area); W column 41 -> 84 um; E column 52 -> 95 um;
  Z strips 43.2 -> 64.8 um tall; core band c 324 x 149 -> 324 x 235 um (starts at the reciprocal's top edge);
  macros stay on the 43.2 lattice (zh0/zh2 x 43.2 -> 86.4, zh1/zh3 x 518.4 -> 561.6, zh2/zh3 y 345.6 -> 388.8,
  recip x 259.2 -> 302.4); pins follow the same piecewise map (N by x, W/E by y).
Same RTL, ports, parameters, landings and cycles as g7a (bench witnesses = g7a's).  The die slot grows by
86.4 um in each dimension (KV die may grow; KV-BIND11 told).
Run: python3 tools/qwen_kv_die/ahub_bo/mk_g7c.py; python3 tools/ref_tile/ref_tile.py gen physical/ref_tile/qkd_ahub_g7c/spec.json
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC, DST = 'qkd_ahub_g7a', 'qkd_ahub_g7c'
W0, H0, W1, H1 = 734.4, 540.0, 820.8, 626.4


def pw(knots, v):
    for (a, fa), (b, fb) in zip(knots, knots[1:]):
        if a <= v <= b:
            return round(fa + (v - a) * (fb - fa) / (b - a), 2)
    raise ValueError(v)


FX = [(0, 0), (43.2, 86.4), (669.6, 712.8), (W0, W1)]
FY = [(0, 0), (194.4, 194.4), (345.6, 388.8), (H0, H1)]
FENCES = {  # region -> new box (old box asserted)
    'c': ('194.4 388.8 518.4 537.84', '237.6 388.8 561.6 624.24'),
    'w': ('2.16 186 43.2 354', '2.16 186 86.4 397.2'),
    'e': ('680.4 186 732.24 310', '723.6 186 818.64 353'),
    'z0': ('43.2 194.4 194.4 237.6', '86.4 194.4 237.6 259.2'),
    'z1': ('518.4 194.4 669.6 237.6', '561.6 194.4 712.8 259.2'),
    'z2': ('43.2 302.4 194.4 345.6', '86.4 324 237.6 388.8'),
    'z3': ('518.4 302.4 669.6 345.6', '561.6 324 712.8 388.8'),
}
AT = {'u_zh0': [86.4, 43.2], 'u_zh1': [561.6, 43.2], 'u_zh2': [86.4, 388.8], 'u_zh3': [561.6, 388.8],
      'u_recip': [302.4, 172.8]}


def main():
    src, dst = ROOT / 'physical/ref_tile' / SRC, ROOT / 'physical/ref_tile' / DST
    dst.mkdir(parents=True, exist_ok=True)
    for f in ('lp_fences.tcl', 'lp_fences_release.tcl'):
        shutil.copy(src / f, dst / f)
    s = json.loads((src / 'spec.json').read_text().replace(SRC, DST))
    assert s['outline'] == {'w': W0, 'h': H0, 'exact': True}, s['outline']
    s['outline'] = {'w': W1, 'h': H1, 'exact': True}
    for c in s['children']:
        c['at'] = AT[c['inst']]
    face = {p: f for f, ps in s['pins'].items() for p in ps}
    for p, (a, b) in s['pin_ranges'].items():
        k = FX if face[p] in ('N', 'S') else FY
        s['pin_ranges'][p] = [pw(k, a), pw(k, b)]
    # measured synthesis area (gate qkd_ahub_g7b-20261020-102723 GATE_AREA, mapped std cells; the area model said 24,876)
    s['std_area_um2'] = 75373.632
    s['job']['tag'] = 'bc'
    s['job']['purpose'] = ('KV-ATTN5 10-20: g7a source re-floorplanned with more channel area (820.8 x 626.4, W/E columns '
                           'and Z strips widened, core band 324 x 235) after g6/g7 GRT congestion; same RTL/cycles.')
    s['floorplan_note'] = ('g7c: g7a/g6a topology with every std-cell region widened (W 84 um, E 95 um, Z strips 64.8 um, '
                           'core band 324 x 235 um above the reciprocal); macros on the 43.2 lattice.')
    s['structural_change'] = (s.get('structural_change', '') + ' g7c: re-floorplanned (+86.4 um each dimension) because '
                              'g6a/g6b/g7a GRT congested at the exact 734.4 x 540 slot.')
    (dst / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
    f = (dst / 'lp_fences.tcl').read_text()
    for r, (old, new) in FENCES.items():
        o = '  %s {{%s}}' % (r, old)
        assert f.count(o) == 1, (r, o)
        f = f.replace(o, '  %s {{%s}}' % (r, new))
    (dst / 'lp_fences.tcl').write_text('# KV-ATTN5 g7c: fence boxes re-floorplanned by tools/qwen_kv_die/ahub_bo/mk_g7c.py\n' + f)
    print(dst)


if __name__ == '__main__':
    main()
