#!/usr/bin/env python3
"""S81-CTRL 10-17: ref_tile specs + pin plans of the S81-DV non-276-b lane relay stations dsfd_dvrly_<W>_<dir>
(RTL rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dvw.sv, the same body as dsfd_dvrly_276_*: ot_s81_rly RSREG=1 = one
register stage per bit, rs through the reset pin register, ck_o = forwarded clock through the kept ckinv pair).

Only the (width, direction) masters the p4i die instantiates are built (owner 10-15: no unused variants):
  70 NS/SN (frame return lanes; p4j, S81-DIE3 10-17: the frame ret / slice rt RTL is 70 b -- the 68-b kits of p4i
  are retired), 512 EW/WE (collective + svc_rs chain), 562 EW/WE/SN (HBM rd), 682 EW/WE/NS (HBM rq).
Each spec is the closed s81dv_rly_276_<dir> spec with the width scaled: the data faces carry W pins at the 276 kit's
pin pitch (N/S: 0.096 um/bit face capacity rule; E/W: 28.08 um for 276 pins, 2.16-um margins), snapped up to the 2.16 lattice; the depth is
the 276 kit's (17.28 um), so the flop density per core area stays the closed kit's.
Usage: gen_dvrly_kits.py [--widths 70 ...] [--owner O --branch B]   (writes tools/ref_tile/specs/s81dv_rly_<W>_<dir>.json + physical/s81_die_pins/dvrlyw/*.tcl)
"""
import copy
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
USED = {70: ('ns', 'sn'), 512: ('ew', 'we'), 562: ('ew', 'we', 'sn'), 682: ('ew', 'we', 'ns')}
LAT = 2.16
# face capacity rule (coordinator 10-17 after s81dv_rly_562_sn-w1 EARLY_FAIL_CONGESTION GRT-0116): >= 0.096 um per bit
# per face per layer pair on the N/S data faces (the 276 kit's 21.6/276 = 0.078 um/bit is below it); E/W faces are at
# 28.08/276 = 0.102 um/bit (M4) already.
FACE_UM_PER_BIT = 0.096


def snap(v):
    return round(math.ceil(round(v / LAT, 6)) * LAT, 2)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--widths', type=int, nargs='*', default=None, help='only these widths (default: every USED width)')
    ap.add_argument('--owner', default='Claude:S81-CTRL')
    ap.add_argument('--branch', default='claude/s81ctrl-1017')
    a = ap.parse_args()
    out = []
    for W, dirs in USED.items():
        if a.widths and W not in a.widths:
            continue
        for d in dirs:
            base = json.loads((ROOT / f'tools/ref_tile/specs/s81dv_rly_276_{d}.json').read_text())
            s = copy.deepcopy(base)
            D = d.upper()
            name, top = f's81dv_rly_{W}_{d}', f'dsfd_dvrly_{W}_{D}'
            s['name'], s['top'] = name, top
            s['sources'] = ['rtl/dsrom_sys/s81_glue/ot_s81_rly.sv', 'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv',
                            'rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dvw.sv']
            if d in ('ns', 'sn'):
                s['outline'] = {'w': max(snap(W * FACE_UM_PER_BIT + 2 * LAT), 12.96), 'h': 17.28}
            else:
                s['outline'] = {'w': 17.28, 'h': max(snap(W * 28.08 / 276 + 2 * LAT), 8.64)}
            s['io_tcl'] = f'physical/s81_die_pins/dvrlyw/{top}.tcl'
            s['structural_change'] = (
                f'{a.owner.split(":")[-1]} 10-17 (p4i/p4j relay views owed, lanes/S81-DIE.md): {W}-b lane station {D[0]}->{D[1]}, the closed '
                f's81dv_rly_276_{d} kit at width {W} (dsfd_rly_masters_dvw.sv: ot_s81_rly W={W} RSREG=1, one register stage, '
                'rs regional reset leaf through the reset pin register, ck = the lane forwarded clock, ck_o through the kept '
                'ckinv pair); recipe 4 flop-first, hold_budget die; data faces at the 276 kit pin pitch, depth 17.28 um. '
                '0 cycles vs the plan (one stage per 405-um hop).')
            j = s['job']
            j.update(owner=a.owner, branch=a.branch, tag='w2' if (d in ('ns', 'sn') and W > 70) else 'w1',
                     purpose=f'S81-DV {W}-b straight lane relay station {top} (recipe 4 flop-first, p4i relay views)',
                     views_to=f'physical/ref_tile/{name}/views', record_to=f'results/rtl/ref_tile/{name}')
            for b in j['benches']:
                b['cmd'] = b['cmd'].replace('dsfd_dvrly_276_' + D, top).replace(' 276 ', f' {W} ').replace(
                    'dsfd_rly_masters_dv276.sv', 'dsfd_rly_masters_dv276.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dvw.sv')
            sp = ROOT / f'tools/ref_tile/specs/{name}.json'
            sp.write_text(json.dumps(s, indent=1) + '\n')
            io = ROOT / s['io_tcl']
            io.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run([sys.executable, str(ROOT / 'tools/ref_tile/spread_face_pins.py'), str(sp), str(io),
                            '--margin', str(LAT)], check=True, cwd=ROOT)
            out.append((name, s['outline']))
    for n, o in out:
        print(n, o)


if __name__ == '__main__':
    main()
