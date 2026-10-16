#!/usr/bin/env python3
"""Attach an m6_pin_grant (tools/hier_contract/m6_pin_grant.py) to GEN18r station specs whose die pin file places
W/E data pins on M6 (station_kits_gen18.py --pin-alt-die = the die generator's --stn-pin-alt rule).

Grant authority: S-DIE r12 lead, el1011-s81die.log 2026-10-15 10:35:22 PDT (main 93c5258e9, --stn-pin-alt: W/E faces
M4 <-> M6 PORT-only at the same coordinates).  The source commit must already hold the spec (without the grant), RTL and
pin file; every M6 pin becomes one explicit port (face, +-0.1 um span along the face, depth <= 0.6 um, area <= 0.1 um2).

    station_m6_grants.py --commit <40-hex source commit> s81fill_hstnh_1024 ...
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/hier_contract'))
import m6_pin_grant as M6  # noqa: E402

SPEC_DIR = ROOT / 'tools/ref_tile/specs_s81_station_gen18r'
PIN_DIR = ROOT / 'physical/s81_die_pins/v22_gen18r_stations'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--commit', required=True)
    ap.add_argument('kits', nargs='+')
    a = ap.parse_args()
    assert re.fullmatch('[0-9a-f]{40}', a.commit), 'full 40-hex source commit'
    for k in a.kits:
        sp = SPEC_DIR / f'{k}.json'
        s = json.loads(sp.read_text())
        s.pop('m6_pin_grant', None)
        ports = []
        for ln in (PIN_DIR / f'{s["top"]}.tcl').read_text().splitlines():
            m = re.search(r'-pin_name \{(\S+)\} -layer M6 -location \{([\d.]+) ([\d.]+)\}', ln)
            if m:
                x, y = float(m[2]), float(m[3])
                ports.append({'name': m[1], 'face': 'W' if x < 1 else 'E', 'span_um': [round(y - 0.1, 4), round(y + 0.1, 4)],
                              'max_depth_um': 0.6, 'max_area_um2': 0.1})
        if not ports:
            print(k, 'no M6 pins, no grant')
            continue
        g = {'schema': M6.SCHEMA, 'master': s['top'],
             'granted_by': 'S-DIE r12 lead, el1011-s81die.log 2026-10-15 10:35:22 PDT (main 93c5258e9 --stn-pin-alt: '
                           'W/E M4<->M6 PORT-only, same coordinates)',
             'reason': 'W/E data face > 12 b/um/layer on M4 alone (verdict 10:00: GRT-0116 / FLOORPLAN_MARGIN pin_density); '
                       'odd face positions on M6 PORT-only = the die generator pins.lef rule; no M6 routing in the tile',
             'source_commit': a.commit, 'source_spec_sha256': M6.spec_digest(s), 'ports': ports}
        M6.validate(g, s['top'])
        s['m6_pin_grant'] = g
        sp.write_text(json.dumps(s, indent=1) + '\n')
        print(k, len(ports), 'M6 ports granted')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
