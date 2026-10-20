#!/usr/bin/env python3
"""Price extracted frame landing paths on existing S81 AR/MTP token DAGs.

Uses the existing immutable geometry and workload; this reports a composed
bound until actual programme measurements qualify the latency extraction.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import frame_return_plan as R
import dv_price as D
ROOT = Path(__file__).resolve().parents[2]

def price(paths, baseline_price):
    inputs, worst = [], 0
    for path in paths:
        s = json.loads(path.read_text())
        flat = R.load_topology(s['topology']['master'])
        added = {}
        for leaf, st in s['station_inputs'].items():
            assert st['all_x_inputs_equal_added_edges']
            x, = st['added_edges']
            assert all(c['added_edges'] == x for c in st['control'].values())
            for row in (0,1):
                name = f'{leaf}.r{row}'
                delta = x + R.leaf_path(s['topology'],name)[0]-R.leaf_path(flat,name)[0]
                added[name] = delta
                worst = max(worst,delta)
        inputs.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                           added_path_edges=added))
    bp=json.loads(baseline_price.read_text())
    geom=bp['geometry']
    D.ENG_SLICE='eng_slice_est' in bp['scenarios']['dv_base']['workloads']['ar']['rules']
    out=dict(schema='opentallas.s81.frame_schedule_cost.v1',status='COMPOSED_NOT_NATIVE',
             programme='Full existing AR and MTP token DAGs; no workload reduction or price change',
             schedule_inputs=inputs,worst_added_edges_per_phase=worst,
             baseline_price=str(baseline_price.relative_to(ROOT)),
             baseline_sha256=hashlib.sha256(baseline_price.read_bytes()).hexdigest(),workloads={})
    for wl,name in [('ar','ds_rom'),('mtp','ds_rom_mtp')]:
        doc=json.loads((D.TP/f'{name}.json').read_text())
        delta,_=D.dv_deltas(doc,geom)
        _,base=D.solve_with_wave(doc,delta)
        extra={}
        for n in doc['nodes']:
            m=re.search(r'r8 die wire (\d+(?:\.\d+)?) cyc over (\d+) phase',n.get('src',{}).get('note','') or '')
            if m and n.get('cls')=='field':
                extra[n['id']]=int(m.group(2))*worst
        merged={k:delta.get(k,0)+extra.get(k,0) for k in delta.keys()|extra.keys()}
        _,new=D.solve_with_wave(doc,merged)
        out['workloads'][wl]=dict(dag_sha256=hashlib.sha256((D.TP/f'{name}.json').read_bytes()).hexdigest(),
                                  baseline_composed_cycles=base,landed_composed_cycles=new,
                                  critical_path_added_cycles=new-base,
                                  composed_e2e_loss_pct=D.ac.loss_pct(base,new),
                                  changed_field_nodes=len(extra),phase_counts=sum(extra.values())//worst)
    out['qualification_note']='The bound charges the worst extracted station+return path once per existing field phase, including MTP wave expansion. RTL frame programme, mutants and physical gates remain required; no accepted-cost ledger entry.'
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('schedules',type=Path,nargs='+')
    ap.add_argument('--baseline-price',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    d=price([p.resolve() for p in a.schedules],a.baseline_price.resolve())
    a.out.write_text(json.dumps(d,indent=1)+'\n')
    print(json.dumps(d['workloads'],indent=1))
