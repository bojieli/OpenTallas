#!/usr/bin/env python3
"""Count every multi-terminal bus and bound its longest branch without assuming RTL direction or equal ages."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'budgets'))
from common import port_xy

CLOCK = {'fclk', 'clock', 'clock_trunk', 'col_clock'}
RESET = {'reset', 'col_reset', 'reset_tree', 'rst'}


def audit(model):
    by = {row[0]: row for row in model['insts']}
    rows = []; missing = []
    source_counts = Counter(b[1] for b in model['buses'] if len(b[3]) > 2)
    for bid, cls, bits, eps in model['buses']:
        if len(eps) <= 2:
            continue
        points = []
        for inst, port, *_ in eps:
            if inst not in by:
                missing.append(dict(bus=bid, inst=inst, port=port))
                continue
            xy, known = port_xy(model, by[inst], port)
            points.append((xy, known, inst, port))
        if not points:
            continue
        # Max Manhattan separation needs only the extrema of x+y and x-y.
        pair = max(((min(points, key=lambda p: p[0][0] + sign * p[0][1]),
                     max(points, key=lambda p: p[0][0] + sign * p[0][1])) for sign in (1, -1)),
                   key=lambda ab: abs(ab[0][0][0] - ab[1][0][0]) + abs(ab[0][0][1] - ab[1][0][1]))
        distance = lambda a, b: abs(a[0][0] - b[0][0]) + abs(a[0][1] - b[0][1])
        first = points[0]; far = max(points, key=lambda p: distance(first, p))
        # Missing pin anchors cannot prove a physical pin-to-pin failure. A
        # rectangle-gap lower bound remains valid for this same longest pair.
        ra, rb = by[pair[0][2]], by[pair[1][2]]
        box_lb = max(0., max(ra[5], rb[5]) - min(ra[5]+ra[7], rb[5]+rb[7])) + \
                 max(0., max(ra[6], rb[6]) - min(ra[6]+ra[8], rb[6]+rb[8]))
        rf, rt = by[first[2]], by[far[2]]
        first_lb = max(0., max(rf[5], rt[5])-min(rf[5]+rf[7], rt[5]+rt[7])) + max(0., max(rf[6], rt[6])-min(rf[6]+rf[8], rt[6]+rt[8]))
        rows.append(dict(bus=bid, bus_class=cls, bits=bits, terminals=len(eps),
            kind='clock' if cls in CLOCK else 'reset' if cls in RESET else 'data_or_control',
            endpoint_anchor_gaps=sum(not p[1] for p in points), unresolved_instances=len(eps)-len(points),
            first_endpoint_branch_um=round(distance(first, far), 3),
            first_endpoint_same_pair_box_gap_lower_bound_um=round(first_lb, 3),
            max_terminal_separation_um=round(distance(*pair), 3),
            same_pair_box_gap_lower_bound_um=round(box_lb, 3),
            longest_pair=[[p[2], p[3]] for p in pair],
            direction='first endpoint is generator ordering only; RTL direction qualification required',
            age='UNPROVED: graph geometry does not establish branch latency/phase or compiler equal-age calendar'))
    rows.sort(key=lambda r: -r['max_terminal_separation_um'])
    return dict(scope='ALL_MULTI_TERMINAL_BUS_GEOMETRY_AUDIT_NOT_RTL_DIRECTION_OR_AGE_QUALIFICATION',
        source_bus_count=len(model['buses']), multi_terminal_bus_count=sum(source_counts.values()),
        source_multi_terminal_classes=dict(source_counts), emitted_rows=len(rows),
        unresolved_endpoints=missing, rows=rows,
        categories={kind:dict(buses=sum(r['kind']==kind for r in rows),
            first_branch_box_gap_over_500=sum(r['kind']==kind and r['first_endpoint_same_pair_box_gap_lower_bound_um']>500 for r in rows),
            with_box_gap_over_500=sum(r['kind']==kind and r['same_pair_box_gap_lower_bound_um']>500 for r in rows),
            with_anchor_span_over_500=sum(r['kind']==kind and r['max_terminal_separation_um']>500 for r in rows),
            age_qualified=0) for kind in ('data_or_control','reset','clock')})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model', required=True, type=Path);ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args();raw=a.model.read_bytes();model=json.loads(gzip.decompress(raw) if raw[:2]==b'\x1f\x8b' else raw)
    report=audit(model);report['source_model_sha256']=hashlib.sha256(raw).hexdigest()
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('rows','unresolved_endpoints')}))


if __name__=='__main__':main()
