#!/usr/bin/env python3
"""age_kit.py BASE OUT N S [AGE_N AGE_S]: derive a G-unit HOP age kit from BASE (the committed 49f8f8f84 m_old_age kit,
lowered by gu_kit/lower_gu at HC_LAT 759/757, delta 0): every HC coefficient row (kind 0xF, row 1000..1013) on vo_n /
vo_s moves by (N - 759) / (S - 757) edges -- exactly what lower_gu.lower() does for HC_LAT_N/S (lower_gu.py:301: CTL row
edge = HC row origin + HC_LAT) -- router rows, stimulus, host boot and cw expectations stay byte-identical.  tb.args
carries +HC_AGE_N/S (default N/S) = the measured-age contract tb_gu_layer checks at the actual port-capture edges."""
import json, re, shutil, sys
from pathlib import Path
base, out, n, s = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
an = int(sys.argv[5]) if len(sys.argv) > 5 else n
as_ = int(sys.argv[6]) if len(sys.argv) > 6 else s
B_N, B_S = 759, 757
if out.exists(): shutil.rmtree(out)
shutil.copytree(base, out)
moved = {}
for f, d in (('exp_n.memh', n - B_N), ('exp_s.memh', s - B_S)):
    lines = (out / f).read_text().split('\n'); k = 0
    for i, ln in enumerate(lines):
        if not ln.strip(): continue
        v = int(ln, 16); cyc, val = v >> 276, v & ((1 << 276) - 1)
        kind, row = (val >> 57) & 0xF, (val >> 47) & 0x3FF
        if kind == 0xF and 1000 <= row < 1014:
            lines[i] = format(((cyc + d) << 276) | val, '0%dx' % len(ln)); k += 1
    (out / f).write_text('\n'.join(lines)); moved[f] = k
a = (out / 'tb.args').read_text()
a = re.sub(r'\+HC_AGE_N=\d+', f'+HC_AGE_N={an}', a); a = re.sub(r'\+HC_AGE_S=\d+', f'+HC_AGE_S={as_}', a)
(out / 'tb.args').write_text(a)
j = json.loads((out / 'kit.json').read_text())
j['age_contract_candidate'] = dict(base='49f8f8f84 results/rtl/s81_gunit_pin_age_1019/kits/m_old_age (759/757)',
    delta_vs_saved_HOP=n - B_N, N=n, S=s, tb_age_N=an, tb_age_S=as_, hc_rows_moved=moved)
(out / 'kit.json').write_text(json.dumps(j, indent=1) + '\n')
print(out.name, moved, a.strip()[-60:])
