#!/usr/bin/env python3
"""FT-S81 10-23: ref_tile specs + pin plans of the 70-b horizontal lane relay stations dsfd_dvrly_70_EW / _WE
(RTL rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv70h.sv, the dsfd_dvrly_70_NS body: ot_s81_rly W=70 RSREG=1, one register
stage per bit, full cycle; ck_o = forwarded clock through the kept ckinv pair), used as feedthrough stations inside the
S81 frames.  Same rule as tools/s81_ctrl/gen_dvrly_kits.py (the 512/562/682 EW/WE kits): the closed s81dv_rly_276_<dir>
spec with the width scaled -- E/W data faces at the 276 kit pin pitch (28.08 um per 276 pins + 2 x 2.16-um margins,
snapped up to the 2.16 lattice), depth 17.28 um -> outline 17.28 x 12.96.
Usage: gen_dvrly70h_kits.py [--owner O --branch B --tag T]   (writes tools/ref_tile/specs/s81dv_rly_70_{ew,we}.json +
physical/s81_die_pins/dvrlyw/dsfd_dvrly_70_{EW,WE}.tcl)
"""
import argparse
import copy
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAT = 2.16
W = 70
SRCS = ['rtl/dsrom_sys/s81_glue/ot_s81_rly.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv',
        'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv70h.sv']


def snap(v):
    return round(math.ceil(round(v / LAT, 6)) * LAT, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--owner', default='Claude:FT-S81 sub')
    ap.add_argument('--branch', default='claude/ft-s81-1023')
    ap.add_argument('--tag', default='h1')
    a = ap.parse_args()
    for d in ('ew', 'we'):
        s = copy.deepcopy(json.loads((ROOT / f'tools/ref_tile/specs/s81dv_rly_276_{d}.json').read_text()))
        D = d.upper()
        name, top = f's81dv_rly_{W}_{d}', f'dsfd_dvrly_{W}_{D}'
        s['name'], s['top'], s['sources'] = name, top, list(SRCS)
        s['outline'] = {'w': 17.28, 'h': max(snap(W * 28.08 / 276 + 2 * LAT), 8.64)}
        s['io_tcl'] = f'physical/s81_die_pins/dvrlyw/{top}.tcl'
        s['structural_change'] = (
            f'FT-S81 10-23 (S81 frame feedthrough stations): {W}-b horizontal lane station {D[0]}->{D[1]}, the closed '
            f's81dv_rly_276_{d} kit at width {W} (dsfd_rly_masters_dv70h.sv: ot_s81_rly W={W} RSREG=1, one register stage '
            '(full cycle), rs regional reset leaf through the reset pin register, ck = the lane forwarded clock, ck_o through '
            'the kept ckinv pair; body = dsfd_dvrly_70_NS); recipe 4 flop-first, hold_budget die; E/W data faces at the 276 '
            'kit pin pitch, depth 17.28 um. 0 cycles vs the plan (one stage per hop).')
        j = s['job']
        j.update(owner=a.owner, branch=a.branch, tag=a.tag,
                 purpose=f'S81-DV {W}-b horizontal lane relay station {top} (recipe 4 flop-first, S81 frame feedthrough)',
                 views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}')
        j['extra_paths'] = ['rtl/dsrom_sys/s81_glue', 'physical/s81_die_pins/dvrly276', 'physical/s81_die_pins/dvrlyw']
        for b in j['benches']:
            b['cmd'] = b['cmd'].replace('dsfd_dvrly_276_' + D, top).replace(' 276 ', f' {W} ').replace(
                'dsfd_rly_masters_dv276.sv', 'dsfd_rly_masters_dv276.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv70h.sv')
        sp = ROOT / f'tools/ref_tile/specs/{name}.json'
        sp.write_text(json.dumps(s, indent=1) + '\n')
        io = ROOT / s['io_tcl']
        subprocess.run([sys.executable, str(ROOT / 'tools/ref_tile/spread_face_pins.py'), str(sp), str(io),
                        '--margin', str(LAT)], check=True, cwd=ROOT)
        print(name, s['outline'])


if __name__ == '__main__':
    main()
