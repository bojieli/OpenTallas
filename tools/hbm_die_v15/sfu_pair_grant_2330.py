#!/usr/bin/env python3
"""Die adoption of a source-pinned compact SFU boundary-leaf candidate."""
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF = 'f8a9ca970'


def blob(path):
    return subprocess.check_output(['git', '-C', str(ROOT), 'show', REF + ':' + path])


def main():
    path = 'physical/hbm_sfu_pair_2330/assignment.json'
    a = json.loads(blob(path))
    width, height = a['outline_um']
    src = 'rtl/hbm_accel/generic/peers/ot_hgi_sfu_lg_pair_leaf.sv'
    assert hashlib.sha256(blob(src)).hexdigest() == a['source_sha256']
    assert len(a['pins']) == 2226
    grouped = defaultdict(list)
    occupied = set()
    for p in a['pins']:
        coord = p['centre_um']
        assert abs((coord - .012) / .048 - round((coord - .012) / .048)) < 1e-6
        assert (p['face'], coord) not in occupied
        occupied.add((p['face'], coord))
        extent = width if p['face'] in 'NS' else height
        assert .012 < coord < extent - .012
        if p['layer'] == 'M5':
            for lo, hi in a['pdn_template']['M5_VDD_VSS_stripes']:
                assert coord + .012 + .024 <= lo + 1e-6 or coord - .012 - .024 >= hi - 1e-6
        grouped[re.sub(r'\[\d+\]$', '', p['port'])].append(p)
    pins = []
    for name, bits in grouped.items():
        coords = [p['centre_um'] for p in bits]
        assert coords == sorted(coords)
        pins.append(dict(name=name if len(bits) == 1 else f'{name}[{len(bits)-1}:0]',
            face=bits[0]['face'], layer=bits[0]['layer'], bit_centres_um=coords,
            span_um=[round(coords[0] - .048, 6), round(coords[-1] + .048, 6)],
            offset=round((coords[0] + coords[-1]) / 2, 6),
            bit_centres_rule='Explicit ascending RTL bit index; exact actual-track centres.'))
    gf = ROOT / 'results/arch/hier_contract_1015/hbm_v15.json'
    g = json.loads(gf.read_text())
    homes = []
    for s in g['slots']:
        if not re.fullmatch(r'sfu_(SW|SE|NW|NE)[0-3]', s['name']):
            continue
        # Keep the old216um outer reservation for incident planning; this leaf
        # occupies its centre. It cannot consume the rest or qualify the core.
        if s.get('grant') != 'compact_sfu_pair_candidate_2330':
            s['reservation_216_2330'] = dict(origin=dict(s['origin']), outline=dict(s['outline']))
        r = s['reservation_216_2330']
        x = round((r['origin']['x'] + (216 - width) / 2) / 43.2) * 43.2
        y = round((r['origin']['y'] + (216 - height) / 2) / 43.2) * 43.2
        assert r['origin']['x'] <= x and x + width <= r['origin']['x'] + 216
        assert r['origin']['y'] <= y and y + height <= r['origin']['y'] + 216
        s['origin'] = dict(x=round(x, 6), y=round(y, 6), orient='R0')
        s.update(outline=dict(w=width, h=height), params=dict(PIN_RST=1),
            grant='compact_sfu_pair_candidate_2330', source=src,
            source_prerequisite=REF, source_sha256=a['source_sha256'],
            assigned_pins_file=path,
            assigned_pins_sha256=hashlib.sha256(blob(path)).hexdigest(),
            assigned_io_tcl='physical/hbm_sfu_pair_2330/io.tcl',
            assigned_io_tcl_sha256=hashlib.sha256(blob('physical/hbm_sfu_pair_2330/io.tcl')).hexdigest(),
            clock_entry=dict(pin='clk', face='N', layer='M5', offset=a['clock_entry']['offset_um']),
            pins=pins, qualified=False,
            normal_edges_each_direction=1, reset_initialization_edges=2,
            notes='Compact actual1112dataFF+1resetFF boundary leaf within old216sq reservation. '
                'Assignment reviewed on actual0.012+n*0.048 tracks and template PG clearance. '
                'Actual ODB PG, fill, CTS/native and full-SFU-core home remain OPEN.')
        if 'pin_windows' in s:
            s['historical_pin_windows_before_2330'] = s.pop('pin_windows')
        s.pop('rtl_pending', None)
        homes.append(s['name'])
    assert len(homes) == 16
    g['sfu_pair_candidate_2330'] = dict(source=REF, homes=homes,
        arithmetic_assignment_checks='PASS2226pins',
        actual_ODB_PG='PENDING', qualified=False,
        core_home='OPEN; boundary leaves do not reserve a complete arithmetic core')
    gf.write_text(json.dumps(g, indent=1) + '\n')
    print('PASS:16compact SFU candidate homes,2226assigned track/PG-template checks; actual ODB pending')


if __name__ == '__main__':
    main()
