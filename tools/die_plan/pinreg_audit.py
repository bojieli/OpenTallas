#!/usr/bin/env python3
"""Compare fresh TT/FF pre/post pad measurements on the SAME RC basis.
This never repairs a design and never upgrades a local or release signoff.
"""
import argparse
import json
import math
from pathlib import Path


def evaluate(before, after):
    reasons = []
    for corner in ('tt', 'ff'):
        a, b = before.get(corner, {}), after.get(corner, {})
        required = ('corner', 'parasitics', 'pinreg_n', 'pinreg_mean_ps', 'bound_ps', 'tol_ps',
                    'group_min_ps', 'group_max_ps', 'group_spread_ps')
        if any(k not in a or k not in b for k in required):
            reasons.append(f'{corner}: missing measurement')
            continue
        numeric = [k for k in required if k not in ('corner', 'parasitics')]
        if any(not isinstance(record[k], (int,float)) or not math.isfinite(record[k]) for record in (a,b) for k in numeric):
            reasons.append(f'{corner}: nonfinite measurement')
            continue
        if a['pinreg_n'] <= 0 or b['pinreg_n'] <= 0:
            reasons.append(f'{corner}: no measured pin registers')
        if a['corner'].lower() != corner or b['corner'].lower() != corner:
            reasons.append(f'{corner}: wrong corner')
        if a['parasitics'] != b['parasitics'] or a['parasitics'] not in ('global_routing', 'spef'):
            reasons.append(f'{corner}: incomparable or unqualified RC basis')
        if a['pinreg_n'] != b['pinreg_n'] or not b['pinreg_n']:
            reasons.append(f'{corner}: boundary membership changed or absent')
        if a['bound_ps'] != b['bound_ps'] or a['tol_ps'] != b['tol_ps']:
            reasons.append(f'{corner}: clock contract changed')
        if abs(b['pinreg_mean_ps']-b['bound_ps']) > b['tol_ps']:
            reasons.append(f'{corner}: insertion mismatch')
        if b['group_spread_ps'] > 20.000001 or b['group_max_ps'] > b['bound_ps']+b['tol_ps']+1e-6:
            reasons.append(f'{corner}: unbalanced or late pin-register groups')
    a, b = before.get('ff', {}), after.get('ff', {})
    fields = ('hold_census_n', 'hold_census_worst_ps', 'hold_census_tns_ps', 'hold_census_margin_n')
    if any(k not in a or k not in b for k in fields) or any(x.get('hold_census_status') not in ('MEASURED', 'NO_TARGETS') for x in (a, b)):
        reasons.append('ff: internal-to-output hold census NOT RUN')
    elif any(not isinstance(record[k], (int,float)) or not math.isfinite(record[k]) for record in (a,b) for k in fields):
        reasons.append('ff: nonfinite hold census')
    else:
        if any(record[k] < 0 for record in (a,b) for k in ('hold_census_n','hold_census_margin_n')):
            reasons.append('ff: invalid hold endpoint count')
        if b['hold_census_n'] > a['hold_census_n'] or b['hold_census_margin_n'] > a['hold_census_margin_n']:
            reasons.append('ff: padding increased internal-to-output hold endpoint work')
        if b['hold_census_worst_ps'] < a['hold_census_worst_ps']-1e-6 or b['hold_census_tns_ps'] < a['hold_census_tns_ps']-1e-6:
            reasons.append('ff: padding worsened internal-to-output hold slack')
    return dict(verdict='FAIL' if reasons else 'PASS', reasons=reasons,
                scope='pin-register pad diagnostic only; full physical and parent signoff still required')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--before', default='pinreg_before')
    parser.add_argument('--after', default='pinreg_after')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('refusing to overwrite an existing verdict')
    try:
        before = {c: json.loads((args.directory/f'{args.before}_{c}.json').read_text()) for c in ('tt','ff')}
        after = {c: json.loads((args.directory/f'{args.after}_{c}.json').read_text()) for c in ('tt','ff')}
        result = evaluate(before, after)
    except (OSError, ValueError, TypeError, KeyError) as error:
        result = dict(verdict='FAIL', reasons=[f'measurement NOT RUN: {error}'])
    args.out.write_text(json.dumps(result, indent=1)+'\n')
    print('PINREG_AUDIT', result['verdict'], '; '.join(result['reasons']))
    raise SystemExit(0 if result['verdict']=='PASS' else 1)
