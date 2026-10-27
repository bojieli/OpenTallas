#!/usr/bin/env python3
"""Compare physical HEAD tree recipes; pure plan construction, no P&R or STA."""
import argparse
import copy
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, os.environ.get('HEAD_TREE_SHARED_TOOLS',
                                 str(Path(__file__).resolve().parent.parent / 'die_plan')))
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


def spread_rows(spec):
    """Pack coincident logical groups into distinct rows inside the same 8.64um island.

    No stages or nets are removed. Every group's complete 2.5um M7 riser envelope
    remains inside that island; the shared builder checks full-body legality.
    """
    out = mirrored(spec)
    groups = defaultdict(list)
    for cell in out['cell_sites'].values():
        groups['g' + str(cell['group'])].append(cell)
    group_of = {}
    for net in out['nets']:
        a, b = net['edge'].split('>')
        group_of[a], group_of[b] = net['drv'], net['load']
    changes = []
    for bucket in out['summary']['packed_islands']:
        gs = [group_of[tag] for tag in bucket['groups']]
        units = [c for g in gs for c in groups[g]]
        cy = (min(c['origin_um'][1] for c in units) + max(c['origin_um'][1] for c in units) + D.ROW_Y) / 2
        limit = min(4.32 - (len(groups[g]) - 1) * D.ROW_Y / 2 - D.C128.STACK_RISER_MAX_UM - .065 for g in gs)
        amplitude = max(0, int((limit + 1e-6) / D.ROW_Y) * D.ROW_Y)
        for index, g in enumerate(gs):
            phase = amplitude * (2 * index / (len(gs) - 1) - 1)
            cells = sorted(groups[g], key=lambda c: c['origin_um'][1])
            y = D.snap(cy + phase - len(cells) * D.ROW_Y / 2, D.ROW_Y)
            for k, cell in enumerate(cells):
                cell['origin_um'][1] = round(y + k * D.ROW_Y, 4)
            changes.append(dict(group=g, phase_um=round(phase,4), units=len(cells)))
    out['summary']['spread_rows'] = changes
    return out


def colored_rows(spec, row_pitch=3.24, column_pitch=0.0):
    """Reserve distinct horizontal corridors for adjacent clock stages.

    This candidate needs a new per-type island census before adoption: unlike
    spread_rows, it intentionally uses adjacent channel sites outside old slots.
    It never enlarges the shared pin-stack or track-search limits.
    """
    out = mirrored(spec)
    groups = defaultdict(list)
    for cell in out['cell_sites'].values():
        groups['g' + str(cell['group'])].append(cell)
    children = defaultdict(list)
    incoming = set()
    horizontal = set()
    vertical = set()
    for net in out['nets']:
        children[net['drv']].append(net['load'])
        incoming.add(net['load'])
        if net['layer'] == 'M8':
            horizontal.update((net['drv'], net['load']))
        else:
            vertical.update((net['drv'], net['load']))
    root, = set(groups) - incoming
    depth, order = {root: 0}, [root]
    for g in order:
        for child in children[g]:
            if child not in depth:
                depth[child] = depth[g] + 1
                order.append(child)
    shifts = []
    for g in sorted(horizontal):
        cells = sorted(groups[g], key=lambda c: c['origin_um'][1])
        phase = ((depth[g] % 3) - 1) * row_pitch
        for cell in cells:
            cell['origin_um'][1] = round(cell['origin_um'][1] + phase, 4)
        shifts.append(dict(group=g, depth=depth[g], phase_um=phase))
    columns = []
    if column_pitch:
        for g in sorted(vertical):
            cells = groups[g]
            if not all(c['part'].startswith('sp') for c in cells):
                raise ValueError('vertical column allocation leaves the soft spine: ' + g)
            phase = ((depth[g] % 3) - 1) * column_pitch
            for cell in cells:
                cell['origin_um'][0] = round(cell['origin_um'][0] + phase, 4)
            columns.append(dict(group=g, depth=depth[g], phase_um=phase))
    # Recompute short corner legs from actual pins. Long trunks keep their axis.
    reps = {g: sorted(cs, key=lambda c: c['origin_um'][1])[0] for g, cs in groups.items()}
    def pin(g, name):
        cell = reps[g]
        return D.C128.pin_xy({'c': dict(x=cell['origin_um'][0], y=cell['origin_um'][1],
            orient=cell['orient'])}, 'c', name, D.ROW_Y)
    layers = {}
    for g, kids in children.items():
        if not kids:
            continue
        d = pin(g, 'Y')
        ps = [pin(child, 'A') for child in kids]
        layers[g] = 'M8' if max(abs(p[0]-d[0]) for p in ps) >= max(abs(p[1]-d[1]) for p in ps) else 'M9'
    for net in out['nets']:
        net['layer'] = layers[net['drv']]
    out['summary']['corridor_rows'] = shifts
    out['summary']['corridor_columns'] = columns
    out['summary']['requires_new_island_census'] = True
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path)
    ap.add_argument('spec', type=Path)
    ap.add_argument('out', type=Path)
    ap.add_argument('--only', choices=['exact', 'mirror_exact', 'spread_rows', 'colored_rows', 'allocated_corridors', 'pg_only_DIAGNOSTIC'], action='append')
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    plan = S.Plan(S.load(args.plan))
    original = json.loads(args.spec.read_text())
    report = {}
    for label, spec in [('exact', copy.deepcopy(original)), ('mirror_exact', mirrored(original)), ('spread_rows', spread_rows(original)),
                        ('colored_rows', colored_rows(original)),
                        ('allocated_corridors', colored_rows(original, row_pitch=4.32, column_pitch=17.28)),
                        ('pg_only_DIAGNOSTIC', mirrored(original))]:
        if args.only and label not in args.only:
            continue
        spec['exact_reserve'] = True
        target = args.out / label
        target.mkdir(exist_ok=True)
        (target / 'explicit_tree.json').write_text(json.dumps(spec, indent=1) + '\n')
        reserve = D.C128.TrackRouter.reserve
        if label == 'pg_only_DIAGNOSTIC':
            # Root-cause isolation only: this intentionally omits inter-clock
            # clearance. Such an output can never qualify as a physical plan.
            D.C128.TrackRouter.reserve = lambda self, shapes: reserve(self, [s for s in shapes if s[2] == 'pg'])
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
        finally:
            D.C128.TrackRouter.reserve = reserve
        if label == 'pg_only_DIAGNOSTIC':
            row['diagnostic_only_ignores_inter_clock_clearance'] = True
        report[label] = row
        print(label, json.dumps(row), flush=True)
        (args.out / 'summary.json').write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    main()
