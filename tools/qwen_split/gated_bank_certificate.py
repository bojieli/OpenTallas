#!/usr/bin/env python3
"""Join actual ICG bank edges to each own-root generated-clock waveform.

This is a behavioral protocol certificate, never a routed timing receipt.
In particular, E_case is not authority to shift a physical root or bank edge.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path


def certify(path, source, age_bands=3):
    content = path.read_text()
    if 'FWD_BENCH PASS 0 errors' not in content or 'FWD_BENCH FAIL' in content:
        raise ValueError('missing clean behavioral PASS')
    rows = []
    count = 8 * 8 * age_bands * 2
    for line in content.splitlines():
        match = re.match(r'GATED_BANK_WINDOW (\S*g_phase\[(\d+)\]\S*\.g\[(\d+)\]) (.*)', line)
        if not match:
            continue
        name, case, bank, values = match.groups()
        case, bank = int(case), int(bank)
        row = dict(path=name, scenario=case, bank=bank)
        for value in values.split():
            key, number = value.split('=')
            row[key] = int(number) if key in ('K', 'checks', 'E_case') else float(number)
        if not (row['checks'] > 0 and .25-1e-6 <= row['min_age_T'] <= row['max_age_T'] <= 3.25+1e-6
                and row['min_overwrite_gap_T'] >= .75-1e-6
                and abs(row['max_age_T']-row['min_age_T']) < 1e-6):
            raise ValueError(f'invalid window: {row}')
        phase = (case // 8) % 8
        extra = (case // 64) % age_bands
        if age_bands == 2:  # Historical grid sampled age bands zero and two.
            extra *= 2
        row.update(phase_index=phase, extra_age_cycles=extra,
                   reset_order=case // (64*age_bands), root_phase_T=phase/8)
        if row['K'] != case % 8:
            raise ValueError('K disagrees with scenario')
        for side, root_phase in [('write', 0), ('read', phase/8)]:
            edge = (row['first_w_ns' if side == 'write' else 'first_r_ns']-5)/10-root_phase
            if abs(edge-round(edge)) > 1e-6:
                raise ValueError('edge is not on declared physical root')
            p = round(edge) % 4
            row[side+'_phase_cycles'] = p
            row[side+'_generated_edges'] = [1+2*p, 2+2*p, 9+2*p]
        nominal = (row['read_phase_cycles']-row['write_phase_cycles']) % 4
        # Keep the actual native root phase. Replacing nominal zero by E_case1
        # would move a real bank edge by T and is forbidden.
        row['actual_nominal_delta_cycles'] = nominal
        age = nominal + phase/8
        if abs(age-row['min_age_T']) > 1e-6:
            raise ValueError('actual waveform does not reproduce measured age')
        capture = row['first_r_ns']
        launch = capture-age*10
        overwrite = launch+40
        n = (launch-row['first_w_ns'])/40
        if abs(n-round(n)) > 1e-6 or n < 0:
            raise ValueError('sampled write is not a real prior bank edge')
        row.update(actual_launch_ns=launch, actual_capture_ns=capture,
                   actual_next_overwrite_ns=overwrite,
                   residual_from_E_case_T=age-row['E_case'])
        rows.append(row)
    if {(r['scenario'], r['bank']) for r in rows} != {(v, b) for v in range(count) for b in range(4)}:
        raise ValueError('incomplete or unexpected scenario/bank coverage')
    if len(rows) != 4*count:
        raise ValueError('duplicate bank evidence')
    return dict(status='BEHAVIORAL_EDGE_WINDOW_PASS_NOT_PHYSICAL_TIMING', source_commit=source,
                witness_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), scenario_count=count,
                period_T=4, high_pulse_T=.5, two_boot_epochs=True, K=list(range(8)),
                checks=sum(r['checks'] for r in rows), min_age_T=min(r['min_age_T'] for r in rows),
                max_age_T=max(r['max_age_T'] for r in rows),
                min_overwrite_gap_T=min(r['min_overwrite_gap_T'] for r in rows),
                clock_family=dict(write='ot_entry_1', read='ot_entry_0',
                    generated_names='qfd_{w,r}bank{0..3}',
                    actual_target='u_land.u_gated.u_{w,r}bank{0..3}/u_cg.u_icg/GCLK'),
                limits=['Test root phase is not permission to alter physical root phase.',
                        'E_case residual cannot replace actual native root and bank waveforms.',
                        'No one-sided uncertainty envelope is qualified by this certificate.',
                        'Routed root references, generated-family census, all data/select/status/reset '
                        'and ICG gating timing remain required, with150/100crossroot reserves.'], rows=rows)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('log', type=Path)
    ap.add_argument('--source', required=True)
    ap.add_argument('--age-bands', type=int, choices=(2, 3), default=3)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = certify(args.log, args.source, args.age_bands)
    args.out.write_text(json.dumps(result, indent=1)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'limits', 'clock_family')}))
