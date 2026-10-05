#!/usr/bin/env python3
"""Offline pin/track predicates; no placement, route or full-access claim."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess

ACCESS = '65b8e35a7'
CAPTURE = 'bc1ccf6fa'
LEF = 'physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.lef'
AUDITOR = 'tools/w10_allport_access_audit.py'
INSPECTION = 'results/uarch/w10_allport_necessary_access/inspection.log'
CAPTURE_RECORD = 'results/uarch/w10_baseline_wake/local_fit_r1/audit.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()

    def read(rev, path):
        return subprocess.check_output(['git', '-C', str(args.repo), 'show', f'{rev}:{path}'])

    def pin(rev):
        return subprocess.check_output(['git', '-C', str(args.repo), 'rev-parse', rev], text=True).strip()

    inputs = {AUDITOR: read(ACCESS, AUDITOR), LEF: read(ACCESS, LEF),
              INSPECTION: read(ACCESS, INSPECTION), CAPTURE_RECORD: read(CAPTURE, CAPTURE_RECORD)}
    ns = {'__file__': str(args.repo / AUDITOR), '__name__': 'pinned_audit_helpers'}
    exec(compile(inputs[AUDITOR], AUDITOR, 'exec'), ns)
    dims, ports, _ = ns['parse_lef'](inputs[LEF].decode())
    old, _, tracks, _, _ = ns['read_inspection'](inputs[INSPECTION].decode())
    capture = json.loads(inputs[CAPTURE_RECORD])['conditional_capture_corridor']
    nm = lambda value: int(Decimal(str(value)) * 1000)
    # Mirror-origin is the candidate's site/track construction in the same pinned tool.
    capture_tool = read(CAPTURE, 'tools/w10_capture_local_fit.py')
    assert b'origin=74250 if mirrored else 6480' in capture_tool
    inputs['tools/w10_capture_local_fit.py'] = capture_tool
    new = []
    for macro in old:
        orient = macro['orientation']
        x = nm(capture['right_macro_x_um'] if orient in {'MY', 'R180'} else capture['left_macro_x_um'])
        y = 74250 if orient in {'MX', 'R180'} else 6480
        new.append(dict(name=macro['name'], orientation=orient,
                        bbox_nm=[x, y, x+dims[0], y+dims[1]]))

    def evaluate(macros):
        records, counts = [], {}
        for macro in macros:
            for name, port in ports.items():
                rect = ns['transform'](port, dims, macro)
                checks = {}
                for layer, axis, lo, hi in [('M4', 'Y', 1, 3), ('M5', 'X', 0, 2)]:
                    origin, pitch = tracks[layer, axis]
                    # Integer interval test finds ANY track, avoiding nearest/tie assumptions.
                    first = (rect[lo]-origin+pitch-1)//pitch
                    last = (rect[hi]-origin)//pitch
                    hit = first <= last
                    checks[layer] = dict(classification='PROVABLE' if hit else 'REFUTED',
                                        track_interval_indices=[first, last],
                                        first_track_nm=origin+first*pitch)
                    counts.setdefault(layer, Counter())[checks[layer]['classification']] += 1
                records.append(dict(macro=macro['name'], orientation=macro['orientation'],
                                    port=name, rect_nm=rect, track_intersection=checks))
        return dict(macros=macros, port_instances=len(records), counts=counts, records=records)

    baseline, candidate = evaluate(old), evaluate(new)
    assert baseline['port_instances'] == candidate['port_instances'] == 1152
    assert baseline['counts']['M4'] == baseline['counts']['M5'] == {'PROVABLE': 1152}
    # Independent nearest-track implementation reproduces each interval classification.
    for result in [baseline, candidate]:
        for record in result['records']:
            r = record['rect_nm']
            for layer, axis, lo, hi in [('M4', 'Y', 1, 3), ('M5', 'X', 0, 2)]:
                origin, pitch = tracks[layer, axis]
                near = origin + round(((r[lo]+r[hi])/2-origin)/pitch)*pitch
                assert (r[lo] <= near <= r[hi]) == (record['track_intersection'][layer]['classification'] == 'PROVABLE')
    result = dict(schema='opentallas.w11.conditional-pin-phase.v1',
                  source_commits=dict(historical_access=pin(ACCESS), conditional_capture=pin(CAPTURE)),
                  source_sha256={p: hashlib.sha256(b).hexdigest() for p, b in inputs.items()},
                  track_grids_nm={f'{layer}_{axis}': list(grid) for (layer, axis), grid in tracks.items()},
                  historical=baseline, conditional=candidate,
                  verdict='BOUNDED_TRACK_INTERSECTION_AUDIT_ONLY', physical_admission=False,
                  full_legal_access_proved=False, final_clock_closure=None,
                  scope='Refuted unextended port/track intersections require an explicit escape conductor hypothesis; they do not prove the macro inaccessible. No candidate adopted or geometry edited.',
                  missing=['Candidate PG geometry: historical PG witnesses do not transfer to moved macros',
                           'Connected escape patches, via enclosure, cut spacing and EOL/PRL legality',
                           'Simultaneous all-port routing and capture endpoint legalization',
                           'CTS buffer area/skew/capacitance and contextual SS setup / FF hold',
                           'Full-element model/area/IR qualification'])
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({key: result[key]['counts'] for key in ['historical', 'conditional']}, sort_keys=True))


if __name__ == '__main__':
    main()
