#!/usr/bin/env python3
"""PATH-KV-SYSC 10-25: give the UCIe PHY abstract (ot_qkvd_ucie_x64_phy, tools/qwen_kv_die/phy_gen.py) a reachable
power interface for the separate VDDPHY domain.

phy_gen.py (via link_phy_gen.write_lef) put VDD / VSS as M4 straps under a full-body M5 obstruction, so no partition
PDN can legally via down to them: the macro was unpowerable.  A hard PHY exposes its supply on its top macro layer
(industry practice: PG pins on the top metal the macro owns, the integrator's grid lands vias on them).  This rewrites
the PG pins as M5 vertical straps (the macro's top layer, obs_max M5) at the partition M5 phase, alternating VDD / VSS,
and cuts the M5 obstruction around them (signal FDI pins at the N edge are untouched).  Pin NAMES stay VDD / VSS: the
partition kit maps this instance's VDD to net VDDPHY (gen_phys.phy_pg_pdn), never core VDD.

usage: phy_pg_view.py IN.lef OUT.lef
"""
import re
import sys
from pathlib import Path

W_STRAP, PITCH, OFF = 0.288, 4.32, 2.064     # partition kit M5 phase (gen_phys.PDN M5 offset 2.064, pitch 4.32)
Y0, Y1 = 0.5, 776.9                          # below the M5 obstruction top (777.2) and the N-edge FDI pins (777.408)
GAP = 0.072                                  # M5 min spacing to the cut obstruction


def main(src, dst):
    text = Path(src).read_text()
    m = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', text)
    w, h = float(m[1]), float(m[2])
    straps = {'VDD': [], 'VSS': []}
    k = 0
    while OFF + k * PITCH + W_STRAP < w - 0.5:
        x = round(OFF + k * PITCH, 4)
        straps['VDD' if k % 2 == 0 else 'VSS'].append([x, Y0, round(x + W_STRAP, 4), Y1])
        k += 1

    def pin(name, use):
        body = '\n'.join(f'      RECT {r[0]:.3f} {r[1]:.3f} {r[2]:.3f} {r[3]:.3f} ;' for r in straps[name])
        return (f'  PIN {name}\n    DIRECTION INOUT ;\n    USE {use} ;\n    PORT\n      LAYER M5 ;\n{body}\n    END\n'
                f'  END {name}')
    text, n1 = re.subn(r'(?ms)^  PIN VDD\s*$.*?^  END VDD\s*$', lambda _: pin('VDD', 'POWER'), text, count=1)
    text, n2 = re.subn(r'(?ms)^  PIN VSS\s*$.*?^  END VSS\s*$', lambda _: pin('VSS', 'GROUND'), text, count=1)
    if n1 != 1 or n2 != 1:
        raise SystemExit('VDD/VSS pins not found')
    om = re.search(r'(?ms)    LAYER M5 ;\n    RECT 0 0 ([\d.]+) ([\d.]+) ;\n', text)
    if not om:
        raise SystemExit('full-body M5 OBS not found')
    ox1, oy1 = float(om[1]), float(om[2])
    xs = sorted(r for v in straps.values() for r in v)
    rects, x = [], 0.0
    for r in xs:
        if r[0] - GAP > x:
            rects.append([x, 0.0, round(r[0] - GAP, 4), oy1])
        rects.append([r[0] - GAP, 0.0, r[2] + GAP, round(Y0 - GAP, 4)])     # below the strap
        rects.append([r[0] - GAP, round(Y1 + GAP, 4), r[2] + GAP, oy1])     # above the strap
        x = round(r[2] + GAP, 4)
    if x < ox1:
        rects.append([x, 0.0, ox1, oy1])
    rects = [[round(v, 4) for v in q] for q in rects if q[2] > q[0] and q[3] > q[1]]
    obs = '    LAYER M5 ;\n' + ''.join(f'    RECT {q[0]:.4f} {q[1]:.4f} {q[2]:.4f} {q[3]:.4f} ;\n' for q in rects)
    text = text[:om.start()] + obs + text[om.end():]
    hdr = ('# PATH-KV-SYSC 10-25 phy_pg_view.py: PG pins moved M4 (under full M5 OBS, unreachable) -> M5 top-layer '
           f'straps ({len(straps["VDD"])} VDD / {len(straps["VSS"])} VSS, {W_STRAP} um @ {PITCH} um); signal pins unchanged\n')
    Path(dst).write_text(hdr + text)
    print(f'VDD {len(straps["VDD"])} VSS {len(straps["VSS"])} M5 OBS rects {len(rects)}')


if __name__ == '__main__':
    main(*sys.argv[1:3])
