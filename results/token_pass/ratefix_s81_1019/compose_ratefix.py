#!/usr/bin/env python3
"""S81-RATEFIX 10-19: re-measure the S81 token with tools/toksim_s81_compose.py after each rate fix.
Each scenario = the committed TOKSIM-S81 element records (results/token_pass/measured_s81_1019/elements) + the
scenario's override records (scenarios/<name>/*.json, loaded after them, so they win per op).  Writes
results/token_pass/ratefix_s81_1019/<name>/cycles.json and prints AR / MTP tok/s.  Nothing is re-priced."""
import json,shutil,sys,importlib.util
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[2]
sp=importlib.util.spec_from_file_location('tc',ROOT/'tools/toksim_s81_compose.py');tc=importlib.util.module_from_spec(sp);sp.loader.exec_module(tc)
SC=json.loads((H/'scenarios.json').read_text())
rows=[]
for name,files in SC.items():
    d=H/name/'elements'
    if d.exists():shutil.rmtree(d)
    d.mkdir(parents=True)
    for f in sorted((ROOT/'results/token_pass/measured_s81_1019/elements').glob('*.json')):shutil.copy(f,d/f.name)
    for f in files:shutil.copy(H/'overrides'/f,d/('zzz_'+f))
    r=tc.build(d)
    (H/name/'cycles.json').write_text(json.dumps(r,indent=1,sort_keys=True)+'\n')
    a,m=r['workloads']['ar'],r['workloads']['mtp']
    rows.append(dict(scenario=name,overrides=files,ar_cycles=a['T_cycles_fixed'],ar_tok_s=a['tok_s'],ar_solved_tok_s=a['tok_s_solved'],
        mtp_step_cycles=m['T_cycles_fixed'],mtp_tok_s=m['tok_s'],price_ar=a['price_of_record'],price_mtp=m['price_of_record'],
        mu=r['multi_user']))
    print(f"{name:28s} AR {a['T_cycles_fixed']:>12,.0f} cyc {a['tok_s']:>8,.1f} tok/s (solved {a['tok_s_solved']:,.1f}) | MTP {m['T_cycles_fixed']:>12,.0f} {m['tok_s']:>8,.1f} tok/s | MU {r['multi_user']['ar']['aggregate_tok_s']:,.0f}/{r['multi_user']['mtp']['aggregate_tok_s']:,.0f}")
(H/'summary.json').write_text(json.dumps(rows,indent=1)+'\n')
