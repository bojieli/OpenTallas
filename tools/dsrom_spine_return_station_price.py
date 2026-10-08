#!/usr/bin/env python3
"""Conditional +1 return-station sensitivity; preserves selected levers and headlines."""
import argparse
import hashlib
import json
from pathlib import Path
import dsrom_field_reprice_r8 as R
import dsrom_1m_measure as M
import dsrom_1m_allmeasured_adapters as A
import dsrom_closure_cost_ledger as L

ROOT = Path(__file__).resolve().parents[1]


def price():
    geom = A.FIELD_GEOM
    geo = R.load_geo(geom)
    wire = R.wire_fn(geo, R.hub_terms(geo))
    reps = {v['rep']: v['layers'] for v in M.TYPES.values()}
    rows = []
    inputs = [Path(__file__), ROOT/'tools/dsrom_field_reprice_r8.py',
              ROOT/'tools/dsrom_1m_measure.py', ROOT/'tools/dsrom_closure_cost_ledger.py']
    inputs += list(L.LEV.parent.glob('*.json'))
    inputs += list((ROOT/'results/rtl/dsrom_1m_allmeasured_20261004').glob('*.json'))
    inputs += [ROOT/'tools/dsrom_1m_allmeasured.py', ROOT/'tools/dsrom_1m_allmeasured_adapters.py']
    inputs += [R.geo_path(d, geom) for d in R.DIES if R.geo_path(d, geom).exists()]
    baseline = L.compose([x[0] for x in L.ITEMS])
    for cfg in ('asbuilt_qelem10', 'pq_qelem'):
        source = R.OUT / R.CONFIGS[cfg][0]
        inputs.append(source)
        regions = R.load_regions(source)
        before = R.summarise(R.node_table(regions, lambda r: wire[r], per_phase_extra=0))
        after = R.summarise(R.node_table(regions, lambda r: wire[r], per_phase_extra=1))
        adds, nodes = [], {}
        for name in before:
            delta = after[name]['total_cycles'] - before[name]['total_cycles']
            assert delta >= 0
            nodes[name] = dict(delta_cycles=delta, before=before[name], after=after[name])
            if name.startswith('E'):
                names = [name]
            else:
                layer, suffix = name.split('.', 1)
                names = [f'L{x}.{suffix}' for x in reps[int(layer[1:])]]
            adds += [(n, delta, 0.0) for n in names if delta]
        composed = L.compose([x[0] for x in L.ITEMS], extra=[
            ('return_station_sensitivity', 'Conditional +1 cycle on each return crossing using measured region ordering', adds)])
        rows.append(dict(configuration=cfg, regions=str(source.relative_to(ROOT)), nodes=nodes,
            expanded_additions=adds, expanded_sum_cycles=sum(x[1] for x in adds),
            baseline_AR_tok_s=baseline[0], conditional_AR_tok_s=composed[0],
            conditional_AR_latency_delta_ns=(1/composed[0]-1/baseline[0])*1e9,
            baseline_MTP_tok_s=baseline[1], conditional_MTP_tok_s=composed[1],
            scope='Conditional timing sensitivity using historical source-pinned measurements; not proof that new PQ/BF/1792 geometry has these phase timings'))
    return dict(schema='opentallas.s81.return-station-sensitivity.v1', adopted=False,
        incremental_return_cycles=1, geometry=geom,
        method='Reprice measured region/node schedules with per_phase_extra=1; retain critical-stage selection; expand representative layer types; run current whole-token DAG composer with temporary candidate additions',
        excluded='No performance credit or new RTL exactness; actual1792 remap and new station measurements require fresh phase records',
        sources_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        variants=rows)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, required=True); args=ap.parse_args()
    result=price(); args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps([{k:r[k] for k in ('configuration','expanded_sum_cycles','conditional_AR_latency_delta_ns')} for r in result['variants']]))
