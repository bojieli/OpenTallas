#!/usr/bin/env python3
"""Report measured physical-clock pin and boundary-reference arrival distributions.

Use raw propagated OpenSTA arrivals and source-exact per-child insertion R.
No estimated, nearest-neighbour, scalar-parent, or negative-phase substitution.
"""
import argparse
import json
import math
from pathlib import Path
import statistics
from physical_die_clock_sta import sha


def stats(values):
    values=list(values)
    if not values:return None
    if not all(math.isfinite(v) for v in values):raise ValueError('non-finite clock arrival')
    return dict(n=len(values),min_ps=min(values),mean_ps=statistics.mean(values),
                max_ps=max(values),spread_ps=max(values)-min(values))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('coverage','sta','out'):ap.add_argument('--'+key,type=Path,required=True)
    a=ap.parse_args()
    coverage=json.loads(a.coverage.read_text())
    rec=dict(schema='opentallas.s81.physical_clock_arrival_report.v1',scope=coverage['scope'],
             native_clock_qualified=False,coverage_sha256=sha(a.coverage),
             missing_entry_loads=coverage['missing_entry_loads'],
             missing_per_child_insertions=len(coverage.get('missing_insertions',{})),
             actual_physical_compensation=False,corners={})
    for corner in ('tt','ff'):
        path=a.sta/f'{corner}_arrivals.tsv'
        arrivals={}
        for line in path.read_text().splitlines():
            key,late,early=line.split('\t')
            if key in arrivals:raise ValueError(f'duplicate arrival pin {key}')
            arrivals[key]=dict(late_ps=float(late),early_ps=float(early))
        if len(arrivals)!=coverage['selected_entries']:raise ValueError('incomplete propagated arrival coverage')
        pins={}
        for key,values in arrivals.items():
            r=coverage.get('per_child_insertions',{}).get(key,{}).get('by_corner',{}).get(corner)
            pins[key]=dict(values,real_boundary_insertion=r)
            if r:
                pins[key].update(boundary_late_ps=values['late_ps']+r['mean_ps'],
                                 boundary_early_ps=values['early_ps']+r['mean_ps'])
        rec['corners'][corner]=dict(arrivals_sha256=sha(path),
            pin_late=stats(p['late_ps'] for p in pins.values()),
            pin_early=stats(p['early_ps'] for p in pins.values()),
            real_R_mean=stats(p['real_boundary_insertion']['mean_ps'] for p in pins.values() if p['real_boundary_insertion']),
            real_R_spread=stats(p['real_boundary_insertion']['spread_ps'] for p in pins.values() if p['real_boundary_insertion']),
            boundary_late_subset=stats(p['boundary_late_ps'] for p in pins.values() if 'boundary_late_ps' in p),
            boundary_early_subset=stats(p['boundary_early_ps'] for p in pins.values() if 'boundary_early_ps' in p),
            pins=pins)
    a.out.write_text(json.dumps(rec,indent=1)+'\n')
    print(json.dumps({c:{k:v for k,v in d.items() if k!='pins'} for c,d in rec['corners'].items()},indent=1))


if __name__=='__main__':main()
