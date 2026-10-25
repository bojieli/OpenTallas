"""HBM integration of shared exact per-bit feedthrough station siting.

Run after contents and centre-based stations, before clock/reset and latency
tables. Explicit cell sites prove reach and cell placement, not channel routing.
Every added cycle is returned for the model/native compiler.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'die_plan'))
import schema as S
import bit_stations as shared


def repair(plan, log=print, only_types=None):
    before = S.Plan(json.loads(json.dumps(plan)))
    old = {lid: before.lane_latency(lid)['cycles'] for lid in before.lanes}
    report = shared.repair(plan, log=log, only_types=only_types, avoid_core_routes=True)
    report['unfixed'] = [r for r in shared.geometry_failures(plan) if only_types is None or r['type'] in only_types]
    after = S.Plan(plan)
    report['lane_cycles'] = [dict(lane=lid, before=old[lid], after=after.lane_latency(lid)['cycles'],
                                 added=after.lane_latency(lid)['cycles']-old[lid])
                             for lid in after.lanes if after.lane_latency(lid)['cycles'] != old[lid]]
    report['pad_conflicts'] = after.bus_pads()[1]
    if report['unfixed']:
        raise ValueError(f"HBM actual-bit FT reach remains infeasible: {report['unfixed']}")
    if report['pad_conflicts'] and only_types is None:
        raise ValueError(f"HBM actual-bit FT change needs type-uniform R8 pads: {report['pad_conflicts']}")
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
    report=repair(plan,only_types=a.types.split(',') if a.types else None)
    p=S.Plan(plan)
    plan['latency']['lanes']={lid:p.lane_latency(lid) for lid in p.lanes}
    Path(a.out).write_text(json.dumps(plan,indent=0)+'\n')
    Path(a.report).write_text(json.dumps(report,indent=1)+'\n')


if __name__=='__main__':main()
