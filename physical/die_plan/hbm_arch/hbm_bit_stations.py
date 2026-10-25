"""HBM integration of shared exact per-bit feedthrough station siting.

Run after contents and centre-based stations, before clock/reset and latency
tables. Explicit cell sites prove reach and cell placement, not channel routing.
Every added cycle is returned for the model/native compiler.
"""
import json
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'die_plan'))
import schema as S
import bit_stations as shared


class RepairFailure(ValueError):
    def __init__(self, report):
        self.report = report
        super().__init__(f"HBM FT repair incomplete: {report['type_failures']}; "
                         f"unfixed geometry={len(report['unfixed'])}, pads={len(report['pad_conflicts'])}")


def repair(plan, log=print, only_types=None):
    before = S.Plan(json.loads(json.dumps(plan)))
    old = {lid: before.lane_latency(lid)['cycles'] for lid in before.lanes}
    selected = set(only_types) if only_types is not None else {tn for tn,t in plan['partition_types'].items()
                                                                      if t.get('ft_slots') and not t.get('hard')}
    report = dict(checked=0, added=[], slots=[], type_failures=[])
    for tn in sorted(selected):
        log(f'HBM actual-bit FT type {tn}')
        original = copy.deepcopy(plan['partition_types'][tn])
        try:
            row = shared.repair(plan, log=log, only_types=[tn], avoid_core_routes=True)
        except ValueError as error:
            plan['partition_types'][tn] = original
            report['type_failures'].append(dict(type=tn, reason=str(error)))
            log(f'HBM actual-bit FT type {tn} FAIL: {error}')
            continue
        report['checked'] += row['checked']
        report['added'].extend(row['added'])
        report['slots'].extend(row['slots'])
    report['unfixed'] = [r for r in shared.geometry_failures(plan) if only_types is None or r['type'] in only_types]
    after = S.Plan(plan)
    report['lane_cycles'] = [dict(lane=lid, before=old[lid], after=after.lane_latency(lid)['cycles'],
                                 added=after.lane_latency(lid)['cycles']-old[lid])
                             for lid in after.lanes if after.lane_latency(lid)['cycles'] != old[lid]]
    report['pad_conflicts'] = after.bus_pads()[1]
    if report['type_failures'] or report['unfixed'] or (report['pad_conflicts'] and only_types is None):
        report['verdict'] = 'FAIL'
        raise RepairFailure(report)
    report['verdict'] = 'GEOMETRY PASS; channel capacity still needs PROTO'
    report['scope'] = 'geometry-only selected-type pilot' if only_types is not None else 'all FT types; PROTO routing remains required'
    log(f"HBM actual-bit FT: {report['checked']} slots, {len(report['added'])} grew, "
        f"{len(report['lane_cycles'])} lane cycles changed; routing PROTO still required")
    return report


def main():
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan');ap.add_argument('--out',required=True);ap.add_argument('--report',required=True)
    ap.add_argument('--types')
    a=ap.parse_args();plan=json.loads(Path(a.plan).read_text())
    failed = False
    try:
        report=repair(plan,only_types=a.types.split(',') if a.types else None)
    except RepairFailure as error:
        report=error.report;failed=True
        plan['note']=plan.get('note','')+' | DIAGNOSTIC ONLY: actual-bit FT repair incomplete; see report'
    p=S.Plan(plan)
    plan['latency']['lanes']={lid:p.lane_latency(lid) for lid in p.lanes}
    Path(a.out).write_text(json.dumps(plan,indent=0)+'\n')
    Path(a.report).write_text(json.dumps(report,indent=1)+'\n')
    return int(failed)


if __name__=='__main__':sys.exit(main())
