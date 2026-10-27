#!/usr/bin/env python3
"""Compare physical HEAD tree recipes; pure plan construction, no P&R or STA."""
import argparse
import copy
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'die_plan'))
import die_clock_mesh as D
import schema as S


def mirrored(spec):
    out = copy.deepcopy(spec)
    groups = defaultdict(list)
    for cell in out['cell_sites'].values():
        groups['g' + str(cell['group'])].append(cell)
    children = defaultdict(list)
    for net in out['nets']:
        children[net['drv']].append(net['load'])
    changed = 0
    for g, cells in groups.items():
        if not children[g]:
            continue
        x = cells[0]['origin_um'][0]
        dx = sum(groups[c][0]['origin_um'][0] - x for c in children[g])
        if dx < -1e-6:
            for cell in cells:
                cell['orient'] = 'MY'
            changed += 1
    out['summary']['westward_mirrored_groups'] = changed
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path)
    ap.add_argument('spec', type=Path)
    ap.add_argument('out', type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    plan = S.Plan(S.load(args.plan))
    original = json.loads(args.spec.read_text())
    report = {}
    for label, spec in [('exact', copy.deepcopy(original)), ('mirror_exact', mirrored(original))]:
        spec['exact_reserve'] = True
        target = args.out / label
        target.mkdir(exist_ok=True)
        (target / 'explicit_tree.json').write_text(json.dumps(spec, indent=1) + '\n')
        try:
            cells, nets, ports, meta = D.build_explicit(spec, plan, ndr='16w',
                root_um=plan.raw['clock']['spine']['root_um'] if hasattr(plan, 'raw') else None)
        except D.C128.PlanError as error:
            row = dict(verdict='FAIL', counts=dict(Counter(r['kind'] for r in error.rows)), errors=len(error.rows))
            (target / 'plan_errors.json').write_text(json.dumps(dict(error=str(error), rows=error.rows), indent=1) + '\n')
        else:
            row = dict(verdict='PASS', meta=meta['meta'])
            (target / 'mesh.json').write_text(json.dumps(meta) + '\n')
            (target / 'place.json').write_text(json.dumps(cells) + '\n')
            (target / 'nets.json').write_text(json.dumps(dict(nets=nets, ports=ports)) + '\n')
        report[label] = row
        print(label, json.dumps(row), flush=True)
        (args.out / 'summary.json').write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    main()
