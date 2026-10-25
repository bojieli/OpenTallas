"""QC actual-bit FT reach and macro-free cell sites (owner405um rule).

Coreless chains follow each bit's own Z route. Core-bearing types use the shared
row allocator and serialize exact internal cell sites consumed by face_flops.
No existing station/cycle is removed; all additions are returned to the caller.
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'tools' / 'die_plan'))
sys.path.insert(0, str(HERE.parents[2]))
import check
import gen_phys
import schema as S
import ft_sites
from tools.die_trial.legal_sites import RowAllocator


def geometry_failures(raw):
    """Use actual bit faces and explicit cell centres, matching the G2 vehicle."""
    model = S.Plan(raw)
    limit = float(raw.get('budgets', {}).get('ft_station_max_um', 405.0))
    failures = []
    for tn, ty in model.types.items():
        if not ty.get('ft_slots'):
            continue
        pins = {(b, i): (x, y, face) for b, i, _, x, y, face in gen_phys.type_pins(model, tn)}
        boxes = [(c['origin_um'][0], c['origin_um'][1], c['origin_um'][0]+c['outline_um'][0],
                  c['origin_um'][1]+c['outline_um'][1]) for c in ty.get('hard_cores', [])]
        def inset(p):
            x, y, face = p
            return {'W': (x+1, y), 'E': (x-1, y), 'S': (x, y+1), 'N': (x, y-1)}[face]
        for slot in ty['ft_slots']:
            name = slot['name']; k = int(slot.get('stations', 1)); worst = 0.; inside = 0
            if 'bit_sites_um' in slot and len(slot['bit_sites_um']) != k-1:
                failures.append(dict(type=tn, slot=name, reason='station count changed after explicit allocation'))
                continue
            for bit in range(slot['width']+1):
                a = pins.get((name+'_i', bit)); b = pins.get((name+'_o', bit))
                if a is None or b is None:
                    continue
                pa, pb = inset(a), inset(b); path = check.zroute(pa, pb, a[2], b[2]); length = check.plen(path)
                points = [pa]
                for j in range(1, k):
                    if 'bit_sites_um' in slot:
                        q = slot['bit_sites_um'][j-1][bit]; cell = slot['bit_site_cell_um']
                        point = (q[0]+cell[0]/2, q[1]+cell[1]/2)
                    elif slot.get('regs_um'):
                        point = tuple(slot['regs_um'][j])
                    else:
                        point = check.point_at(path, length*j/k)
                    inside += sum(x0 < point[0] < x1 and y0 < point[1] < y1 for x0,y0,x1,y1 in boxes)
                    points.append(point)
                points.append(pb)
                worst = max(worst, *(abs(p[0]-q[0])+abs(p[1]-q[1]) for p,q in zip(points, points[1:])))
            if worst > limit+1e-6 or inside:
                failures.append(dict(type=tn, slot=name, worst_um=round(worst,4), stations_in_core=inside))
    return failures


def repair(raw, log=print, only_types=None):
    model = S.Plan(raw)
    selected = set(only_types) if only_types else {row['type'] for row in geometry_failures(raw)}
    ledger = []
    core_types = []
    limit = float(raw.get('budgets', {}).get('ft_station_max_um', 405.0))
    budget = limit - 2.0  # physical D/Q positions and row snapping, not extra reach
    for tn, ty in model.types.items():
        if tn not in selected or not ty.get('ft_slots'):
            continue
        if ty.get('hard_cores'):
            core_types.append(tn)
            continue
        pins = {(b, i): (x, y, face) for b, i, _, x, y, face in gen_phys.type_pins(model, tn)}
        for slot in ty['ft_slots']:
            name = slot['name']
            lengths = []
            for bit in range(slot['width'] + 1):
                a = pins.get((name + '_i', bit))
                b = pins.get((name + '_o', bit))
                if a is None or b is None:
                    continue
                lengths.append(check.plen(check.zroute(a[:2], b[:2], a[2], b[2])))
            if not lengths:
                continue
            old = int(slot.get('stations', 1))
            new = max(old, math.ceil(max(lengths) / budget))
            # Shared centroid locations can violate actual bit-window tails even
            # when their central route closes. Without macros, each bit's own
            # default path is the direct placement contract.
            declared = bool(slot.get('regs_um') or slot.get('bit_sites_um'))
            slot['stations'] = new
            for key in ('regs_um', 'bit_sites_um', 'bit_site_cell_um'):
                slot.pop(key, None)
            row = dict(type=tn, slot=name, stations=[old, new],
                       worst_paired_bit_um=round(max(lengths) / new, 4),
                       budget_um=budget, mode='per-bit-zroute', removed_centroid_sites=declared)
            ledger.append(row)
            if new != old or declared:
                log(f"bit_stations: {tn}.{name} {old}->{new}, actual max{row['worst_paired_bit_um']:.3f}um; per-bit routes")
    if core_types:
        rows, _ = ft_sites.place(raw, RowAllocator, types=core_types, reach_um=limit, margin=1.0, max_radius_um=40.0)
        for row in rows:
            row['mode'] = 'row-legal-per-bit'
            log(f"bit_stations: {row['type']}.{row['slot']} {row['stations']}, actual max{row['worst_paired_bit_um']:.3f}um; macro-free")
        ledger.extend(rows)
    return dict(checked=len(ledger), added=[r for r in ledger if r['stations'][1] > r['stations'][0]], slots=ledger)


def repair_equalised(raw, log=print):
    """Reach and same-type lane depth must agree after the same plan change."""
    import lane_eq
    before = S.Plan(json.loads(json.dumps(raw)))
    old_depth = {lid: before.lane_natural(lid)['cycles'] for lid in before.lanes}
    report = dict(rounds=[], equalisation=[], lane_cycles=[])
    pending = None
    while True:
        physical = repair(raw, log=log, only_types=pending)
        report['rounds'].append(physical)
        eq = lane_eq.equalise(raw, log=log)
        report['equalisation'].append(eq)
        if eq['unfixed']:
            raise ValueError(f"actual-bit station repair leaves unequal lane families: {eq['unfixed']}")
        if not eq['added']:
            break
        pending = {row['slot'].split('.', 1)[0] for row in eq['added']}
    after = S.Plan(raw)
    report['lane_cycles'] = [dict(lane=lid, before=old_depth[lid], after=after.lane_natural(lid)['cycles'],
                                 added=after.lane_natural(lid)['cycles']-old_depth[lid])
                             for lid in after.lanes if after.lane_natural(lid)['cycles'] != old_depth[lid]]
    report['unfixed'] = geometry_failures(raw)
    if report['unfixed']:
        raise ValueError(f"actual-bit geometry still fails: {report['unfixed']}")
    return report


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan'); ap.add_argument('--out', required=True); ap.add_argument('--report', required=True)
    ap.add_argument('--types')
    ap.add_argument('--equalise', action='store_true')
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    report = repair_equalised(raw) if a.equalise else repair(raw, only_types=a.types.split(',') if a.types else None)
    Path(a.out).write_text(json.dumps(raw, indent=1) + '\n')
    Path(a.report).write_text(json.dumps(report, indent=1) + '\n')

if __name__ == '__main__':
    main()
