#!/usr/bin/env python3
"""Size bounded reset cohorts from a compiled, single-clock-family graph.tsv.

API: reset_cohort_model.py INPUT.tsv OUTPUT.json [--type TYPE] [--hop-um 405]
     [--exclude-root PORT ...] [--no-auto-encoder-exclusion] [--source LABEL]

Rows accepted (tab-separated):
  TAP name x_um y_um
  NODE RRL|COLLECTOR|ENCODER id instance x_um y_um status clock_net [...]
  FANIN RRL|COLLECTOR id instance input_pin comma-separated-actual-RRL-ids (+ token 'root' when the trace
        reached a root-reset-fed register or chain collector; a collector with no RRL id and 'root' is its own cohort)
Other rows (e.g. CORE/MACRO) are retained by the caller's source dump, ignored here.
The caller must extract only the intended logical clock family; this script does
not infer domains or authorize clock rewiring. Geometry is FF-origin based.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import json
from pathlib import Path


def model(path: Path, *, hop_um=405.0, excluded_roots=(), auto_encoder=True,
          type_name=None, source=None):
    if hop_um <= 0:
        raise ValueError('positive modelled hop budget required')
    rows = [s.split('\t') for s in path.read_text().splitlines() if s]
    nodes = defaultdict(list)
    collectors = defaultdict(list)
    owners = defaultdict(set)
    edges = set()
    taps = {}
    root_fed = set()
    encoder = []
    rrl_ff = collector_ff = 0
    for row in rows:
        if row[0] == 'TAP':
            taps[row[1]] = list(map(float, row[2:4]))
        elif row[0] == 'NODE':
            item = dict(name=row[3], xy=list(map(float, row[4:6])),
                        status=row[6], clock_net=row[7])
            if row[1] == 'RRL':
                nodes[int(row[2])].append(item)
                rrl_ff += 1
            elif row[1] == 'COLLECTOR':
                collectors[int(row[2])].append(item)
                collector_ff += 1
            elif row[1] == 'ENCODER':
                encoder.append(item['xy'])
        elif row[0] == 'FANIN':
            toks = [s for s in (row[5] if len(row) > 5 else '').split(',') if s]
            src = {int(s) for s in toks if s != 'root'}
            if row[1] == 'COLLECTOR':
                owners[int(row[2])] |= src
                if 'root' in toks:
                    root_fed.add(int(row[2]))
            elif row[1] == 'RRL':
                edges |= {(s, int(row[2])) for s in src if s != int(row[2])}
    if not nodes or not taps:
        raise ValueError('compiled RRL nodes and explicit local clock taps required')
    root_collectors = {}
    rrl_only = {i: list(members) for i, members in nodes.items()}
    for cid, members in collectors.items():
        actual = owners[cid]
        if not actual and cid in root_fed:
            # RESET-COHORT-1119: driven only by the chain predecessor / a root-reset-fed register (the graph stops at registers):
            # its own cohort member at its fixed site, not an RRL cohort member.
            root_collectors[cid] = members
            continue
        if len(actual) != 1:
            raise ValueError(f'collector{cid} ambiguous/missing actual driver: {sorted(actual)}')
        owner = next(iter(actual))
        if owner not in nodes:
            raise ValueError(f'collector{cid} driver{owner} has no compiled physical node')
        nodes[owner] += members
    for a, b in edges:
        if a not in nodes or b not in nodes:
            raise ValueError(f'actual edge {a}->{b} lacks physical endpoint')

    def points(ids):
        return [n['xy'] for i in ids for n in nodes[i]]

    def bbox(ids):
        xy = points(ids)
        xs, ys = zip(*xy)
        return [min(xs), min(ys), max(xs), max(ys)]

    def span(ids):
        a, b, c, d = bbox(ids)
        return c - a + d - b

    def centroid(ids):
        xy = points(ids)
        return [sum(p[k] for p in xy) / len(xy) for k in (0, 1)]

    def distance(p, q):
        return abs(p[0] - q[0]) + abs(p[1] - q[1])

    def edge_length(edge):
        return distance(centroid([edge[0]]), centroid([edge[1]]))

    excluded = set(excluded_roots)
    enc = dict(FF_count=len(encoder), centroid_um=None, predicted_nearest_root=None)
    if encoder:
        ec = [sum(p[k] for p in encoder) / len(encoder) for k in (0, 1)]
        heavy = min(taps, key=lambda n: (distance(taps[n], ec), n))
        enc.update(centroid_um=ec, predicted_nearest_root=heavy)
        if auto_encoder:
            excluded.add(heavy)
    unknown = excluded - taps.keys()
    if unknown:
        raise ValueError(f'excluded clock roots absent from actual input: {sorted(unknown)}')

    def root_fit(ids):
        pts = points(ids)
        return any(max(distance(p, xy) for p in pts) <= hop_um for name, xy in taps.items() if name not in excluded)

    parent = {i: i for i in nodes}
    groups = {i: {i} for i in nodes}

    def root(i):
        while parent[i] != i:
            i = parent[i]
        return i

    rejected = []
    for a, b in sorted(edges, key=lambda e: (edge_length(e), e)):
        x, y = root(a), root(b)
        if x == y:
            continue
        union = groups[x] | groups[y]
        extent = span(union)
        # FAM-S81-SERDES-R4 11-21 (serdes__t4 J6 rep + a15, CTS fail-closed "unfit light-root groups [222]"): a union whose
        # bbox fits the hop budget can still have no light root within reach of ALL its FFs (two RRL+collector pairs 278 um
        # apart on the die edge, each 171 / 213 um from its own tap, 445 um from any shared one).  Never make a fitting
        # cohort unfit by a union: keep the parts separate (one more cross-group edge, measured by CTS/STA as any other).
        lost_fit = extent <= hop_um and not root_fit(union) and (root_fit(groups[x]) or root_fit(groups[y]))
        if lost_fit:
            rejected.append(dict(edge=[a, b], edge_centroid_span_um=edge_length((a, b)),
                                 rejected_union_bbox_span_um=extent, rejected_union_no_light_root=True))
        elif extent <= hop_um:
            parent[y] = x
            groups[x] = union
            del groups[y]
        else:
            rejected.append(dict(edge=[a, b], edge_centroid_span_um=edge_length((a, b)),
                                 rejected_union_bbox_span_um=extent))


    result_groups = []
    for ids in sorted(groups.values(), key=lambda s: min(s)):
        pts = points(ids)
        choices = []
        for name, xy in taps.items():
            if name in excluded:
                continue
            reach = max(distance(p, xy) for p in pts)
            if reach <= hop_um:
                choices.append(dict(name=name, xy_um=xy,
                                    total_manhattan_um=sum(distance(p, xy) for p in pts),
                                    max_radius_um=reach))
        choices.sort(key=lambda x: (x['total_manhattan_um'], x['name']))
        result_groups.append(dict(key=min(ids), rrl_ids=sorted(ids), FF_count=len(pts),
                                  bbox_um=bbox(ids), bbox_span_um=span(ids),
                                  center_um=centroid(ids),
                                  root_candidates=choices,
                                  light_root_fit=bool(choices)))
    root_groups = []
    for cid, members in sorted(root_collectors.items()):
        pts = [m['xy'] for m in members]
        choices = []
        for name, xy in taps.items():
            if name in excluded:
                continue
            reach = max(distance(p, xy) for p in pts)
            if reach <= hop_um:
                choices.append(dict(name=name, xy_um=xy, total_manhattan_um=sum(distance(p, xy) for p in pts),
                                    max_radius_um=reach))
        choices.sort(key=lambda x: (x['total_manhattan_um'], x['name']))
        xs, ys = zip(*pts)
        root_groups.append(dict(key=f'c{cid}', collector_id=cid, FF_count=len(pts),
                                bbox_um=[min(xs), min(ys), max(xs), max(ys)],
                                bbox_span_um=max(xs) - min(xs) + max(ys) - min(ys),
                                root_candidates=choices, light_root_fit=bool(choices)))
    remaining = [dict(edge=[a, b], centroid_span_um=edge_length((a, b)))
                 for a, b in sorted(edges) if root(a) != root(b)]
    overreach = [dict(edge=[a, b], centroid_span_um=edge_length((a, b)))
                 for a, b in sorted(edges) if edge_length((a, b)) > hop_um]
    endpoint_bounds = [dict(edge=[a, b], maximum_FF_origin_span_um=max(
        distance(x['xy'], y['xy']) for x in rrl_only[a] for y in rrl_only[b]))
        for a, b in sorted(edges)]
    return dict(schema='opentallas.compiled-reset-cohort-model.v1',
                type=type_name, source=source or str(path), input_graph=str(path),
                verdict='ANALYTICAL_BOUNDED_COHORT_PROPOSAL_NOT_CTS_QUALIFIED',
                model_delta=dict(RTL_cells=0, mission_cycles=0, reset_cycles=0),
                hop_budget_um=hop_um,
                algorithm='atomic actual RRL+its compiled collectors, then ascending actual edge distance unions only when whole resulting bbox Manhattan diameter fits hop budget; no all-tree union',
                root_collector_groups=root_groups,
                RRL_modules=len(nodes), RRL_FF=rrl_ff, collector_FF=collector_ff,
                collector_actual_owners={str(c): next(iter(v)) for c, v in owners.items() if v},
                actual_RRL_edges=[list(e) for e in sorted(edges)],
                encoder=enc, excluded_roots=sorted(excluded), groups=result_groups,
                remaining_cross_group_edges=remaining, rejected_unions=rejected,
                actual_centroid_edges_over_budget=overreach,
                atomic_centroid_metric_scope='RRL plus attached collectors; cohort diagnostic only, not data-wire reach',
                actual_RRL_FF_origin_endpoint_bounds=endpoint_bounds,
                actual_RRL_FF_origin_endpoint_bounds_over_budget=[e for e in endpoint_bounds if e['maximum_FF_origin_span_um'] > hop_um],
                endpoint_bound_scope='RRL-only FF-origin pairwise upper bound; actual source-Q/capture-D pin-net extraction remains authoritative', 
                unfit_light_root_groups=[g['key'] for g in result_groups + root_groups if not g['light_root_fit']],
                preserved_contract='caller must preserve actual clock family, source early/late window, FIRM anchors and all RTL/net/stage identities; source latency and actual CTS/repair remain measured gates')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--type', dest='type_name')
    ap.add_argument('--hop-um', type=float, default=405.)
    ap.add_argument('--exclude-root', action='append', default=[])
    ap.add_argument('--no-auto-encoder-exclusion', action='store_true')
    ap.add_argument('--source')
    a = ap.parse_args()
    result = model(a.input, hop_um=a.hop_um, excluded_roots=a.exclude_root,
                   auto_encoder=not a.no_auto_encoder_exclusion,
                   type_name=a.type_name, source=a.source)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(groups=len(result['groups']),
                          max_bbox_span_um=max(g['bbox_span_um'] for g in result['groups']),
                          cross_group_edges=len(result['remaining_cross_group_edges']),
                          overreach_edges=len(result['actual_centroid_edges_over_budget']),
                          unfit_light_root_groups=result['unfit_light_root_groups'],
                          excluded_roots=result['excluded_roots'])))


if __name__ == '__main__':
    main()
