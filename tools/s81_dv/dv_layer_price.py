#!/usr/bin/env python3
"""TOKEN-PASS-S81 (10-18): per-LAYER price of the p4l landed DV die, for the per-layer RTL pass to measure against.

dv_price.py prices the whole token (joint longest path of results/arch/token_path_20261009/ds_rom{,_mtp}.json with the
DV per-node deltas + the p4l land plan, half-cycle hops).  This tool re-uses exactly that machinery (same g facts, same
dv_deltas, same solve) and reports, for each representative layer, the priced layer on the solved DV schedule:
  span   = max(end) - min(start) over the layer's nodes (layer entry to layer exit, what a layer bench measures)
  crit   = sum of (cycles + delta) of the layer's nodes on the token's critical path (its share of the token)
  hub    = the same two numbers on the hub DAG without DV deltas (the 10-09 price the 10-13 vehicle was compared to)
Status COMPOSED_NOT_NATIVE: a price, not a measurement.
"""
import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
import dv_price as dp                                 # noqa: E402
from throughput import accepted_cost as ac            # noqa: E402


def facts(plan_p, land_p, half):
    plan = json.loads(Path(plan_p).read_text())
    f = plan['facts']
    B = {b['name']: b for b in plan['blocks']}
    cen = lambda b: (b['x'] + b['w'] / 2, b['y'] + b['h'] / 2)
    sl = [b for b in plan['blocks'] if b['kind'] == 'slice']
    man = lambda p, q: abs(p[0] - q[0]) + abs(p[1] - q[1])
    g = dict(f, hop_um=f.get('hop_um', 405.0),
             worst_slice_to_gunit_um=max(man(cen(s), cen(B['gunit'])) for s in sl),
             worst_slice_to_edge_um=max(min(man(cen(s), cen(B[c])) for c in (('coll_WS', 'coll_WN', 'coll_ES', 'coll_EN')
                                        if 'coll_WS' in B else ('s_0S', 's_0N', 's_7S', 's_7N'))) for s in sl))
    hl = {l['i']: l['s'] for l in plan['links'] if l['i'].startswith(('hrq_', 'hrd_'))}
    if hl:
        g['hbm_rt_stages'] = max(hl.get(f'hrq_{k}', 0) + hl.get(f'hrd_{k}', 0) for k in {i[4:] for i in hl})
    land = json.loads(Path(land_p).read_text())
    g['landing'] = dict(dp.land_terms(plan, land, half), land_plan=str(land_p))
    g['host_plane'] = dp.host_terms(plan, land, half, landed=True)
    return g


def layer_table(doc, delta, keys):
    nodes = doc['nodes']
    _, e0 = ac.solve(nodes, doc['edges'])
    tot1, e1 = ac.solve(nodes, doc['edges'], delta)
    by = {n['id']: n for n in nodes}
    crit = set(n['id'] for n in nodes if n.get('critical'))
    out = {}
    for name, sel in keys.items():
        ids = [n['id'] for n in nodes if sel(n)]
        if not ids:
            out[name] = None
            continue
        row = {}
        for tag, end, dl in (('hub', e0, {}), ('dv', e1, delta)):
            st = {i: end[i] - by[i]['cycles'] - dl.get(i, 0.0) for i in ids}
            row[f'{tag}_span'] = round(max(end[i] for i in ids) - min(st.values()), 1)
            row[f'{tag}_crit'] = round(sum(by[i]['cycles'] + dl.get(i, 0.0) for i in ids if i in crit), 1)
        row['nodes'] = len(ids)
        row['delta_cycles'] = round(sum(delta.get(i, 0.0) for i in ids), 1)
        row['ops'] = sorted({by[i].get('op', '') for i in ids})[:60]
        out[name] = row
    return out, tot1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', default=str(ROOT / 'results/arch/s81_dv_1016/p4l/plan.json'))
    ap.add_argument('--land-plan', default=str(ROOT / 'results/arch/s81_dv_1016/landing/p4l/land_plan.json'))
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    g = facts(a.plan, a.land_plan, True)
    lay = lambda L: (lambda n: n.get('layer') == L)
    res = dict(schema='opentallas.s81_dv.layer_price.v1', status='COMPOSED_NOT_NATIVE', plan=a.plan, land_plan=a.land_plan,
               half_cycle=True, method=__doc__.strip().splitlines()[0], workloads={})
    for wl, name in (('ar', 'ds_rom'), ('mtp', 'ds_rom_mtp')):
        doc = json.loads((dp.TP / f'{name}.json').read_text())
        delta, _ = dp.dv_deltas(doc, g, 8, 0.0, 1.0, False, ())   # = dv_base (1365.7 AR headline)
        layers = sorted({n.get('layer') for n in doc['nodes'] if isinstance(n.get('layer'), int) and n['layer'] >= 0})
        keys = {f'L{L}': lay(L) for L in layers}
        keys['head'] = lambda n: str(n.get('group', '')).startswith('S0') and any(
            gg['id'] == n.get('group') and gg['kind'] == 'head' for gg in doc['groups'])
        keys['mtp_draft'] = lambda n: 'mtp' in str(n.get('cls', '')).lower() or str(n.get('op', '')).startswith(('mtp', 'draft'))
        tab, tot = layer_table(doc, delta, keys)
        res['workloads'][wl] = dict(token_cycles_dv=round(tot, 1), layers=tab)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    for wl in ('ar', 'mtp'):
        t = res['workloads'][wl]['layers']
        for k in ('L0', 'L1', 'L2', 'L14', 'L20', 'L21', 'L24', 'head', 'mtp_draft'):
            r = t.get(k)
            if r:
                print(f"{wl} {k:9s} hub span {r['hub_span']:9.1f} crit {r['hub_crit']:9.1f} | dv span {r['dv_span']:9.1f} "
                      f"crit {r['dv_crit']:9.1f} delta {r['delta_cycles']:8.1f} nodes {r['nodes']}")


if __name__ == '__main__':
    main()
