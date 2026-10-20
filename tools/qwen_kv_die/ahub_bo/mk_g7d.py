#!/usr/bin/env python3
"""KV-ATTN6 10-20 (tree K.STA.AHUB): qkd_ahub_g7d = qkd_ahub_g7c source/outline, STRUCTURAL re-floorplan of the core access.

Why (measured, not guessed): a zero-iteration GRT on the g7c CTS database (gate qkd_ahub_g7c-20261020-121549, ot-epyc5,
congestion report scratch/kv-attn6/g7c_cong.rpt + congestion.png) puts every hot gcell in ONE place: the z2/z3 strips
under zh2/zh3 and the 64.8 / 43.2 um gaps between zh2/zh3 and the reciprocal (M2/M4/M6 H max 19/13/10, M3/M5 V 15/16),
nets = W/E landing read halves (u_lpl_0/2/3/4_r, u_lpl_1_r) and z2/z3 readers (u_lpl_13/14_r).  Std-cell density is
<= 0.6 everywhere, so more outline (g7c +29 %) did not help: the core band c (above the reciprocal, between zh2 and zh3)
is reachable from the W/E columns and z0/z1 only through those two corner gaps.
g7d opens the core to its neighbours instead of squeezing:
  reciprocal 302.4,172.8 -> 302.4,43.2 (bottom centre, between zh0 and zh1; N-face pins now on the core's S edge);
  zh2/zh3 y 388.8 -> 432 (43.2 lattice), z2/z3 strips 324-388.8 -> 367.2-432 (still on the zh2/zh3 S pin faces);
  core fence c 237.6..561.6 x 388.8..624.24 -> 237.6..561.6 x 259.2..624.24 (324 x 365 um): c now borders the W/E
  corridors (y 259.2-367.2, aligned with the W/E bus pins 194-389) and the z0..z3 strips directly.
Same RTL / ports / params / pins / landings / cycles / outline (820.8 x 626.4) / witnesses as g7c (= g7a source).
Run: python3 tools/qwen_kv_die/ahub_bo/mk_g7d.py; python3 tools/ref_tile/ref_tile.py gen physical/ref_tile/qkd_ahub_g7d/spec.json
"""
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC, DST = 'qkd_ahub_g7c', 'qkd_ahub_g7d'
FENCES = {
    'c': ('237.6 388.8 561.6 624.24', '237.6 259.2 561.6 624.24'),
    'z2': ('86.4 324 237.6 388.8', '86.4 367.2 237.6 432'),
    'z3': ('561.6 324 712.8 388.8', '561.6 367.2 712.8 432'),
}
AT = {'u_zh0': [86.4, 43.2], 'u_zh1': [561.6, 43.2], 'u_zh2': [86.4, 432.0], 'u_zh3': [561.6, 432.0],
      'u_recip': [302.4, 43.2]}


def main():
    src, dst = ROOT / 'physical/ref_tile' / SRC, ROOT / 'physical/ref_tile' / DST
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy(src / 'lp_fences_release.tcl', dst / 'lp_fences_release.tcl')
    s = json.loads((src / 'spec.json').read_text().replace(SRC, DST))
    for c in s['children']:
        c['at'] = AT[c['inst']]
    s['job']['tag'] = 'bd'
    s['job']['purpose'] = ('KV-ATTN6 10-20: g7c outline with the core opened to W/E/Z (reciprocal to the bottom centre, '
                           'zh2/zh3 up 43.2, core fence 324 x 365) after the g7c GRT hot spots at the core corner gaps.')
    s['floorplan_note'] = ('g7d: reciprocal bottom centre (302.4, 43.2); zh0/zh1 bottom corners, zh2/zh3 top corners '
                           '(y 432); core c 237.6-561.6 x 259.2-624.24 borders the W/E corridors and all Z strips.')
    s['structural_change'] = (s.get('structural_change', '') + ' g7d: core access re-floorplanned (reciprocal moved below '
                              'the core) because g7c GRT hot spots sit in the zh2/zh3-reciprocal corner gaps.')
    (dst / 'spec.json').write_text(json.dumps(s, indent=1) + '\n')
    f = (src / 'lp_fences.tcl').read_text()
    for r, (old, new) in FENCES.items():
        o = '  %s {{%s}}' % (r, old)
        assert f.count(o) == 1, (r, o)
        f = f.replace(o, '  %s {{%s}}' % (r, new))
    (dst / 'lp_fences.tcl').write_text('# KV-ATTN6 g7d: fence boxes re-floorplanned by tools/qwen_kv_die/ahub_bo/mk_g7d.py\n' + f)
    print(dst)


if __name__ == '__main__':
    main()
