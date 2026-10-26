"""Unadopted clock-ABI proposal; feed fresh P3c all-FF geometry before use.
No P&R/STA. Exposes density taps as real die-spine terminals.
"""
import argparse,json,sys
from collections import Counter
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/die_plan'))
import schema,taps
p=argparse.ArgumentParser();p.add_argument('geometry');p.add_argument('--out',required=True);p.add_argument('--scope',required=True);a=p.parse_args()
g=json.load(open(a.geometry));pos=g['positions'];names=g.get('registers',[n for n in pos if '$_DFF' in n]);bins=Counter((int(pos[n][0]//10)*10+5,int(pos[n][1]//10)*10+5) for n in names)
out=Path(a.out);out.mkdir(parents=True,exist_ok=True);bf=out/'clock_bins.json'
bf.write_text(json.dumps(dict(bin_um=10,bins=[[x,y,n] for (x,y),n in sorted(bins.items())]),indent=1)+'\n')
plan=json.load(open(root/'physical/die_plan/qwen_compute/die_plan.json'));P=schema.Plan(plan)
before=schema.tap_grid(P,'native59')
clock=plan['partition_types']['native59']['clock']
clock.update(tap_mode='density',sink_bins_file=str(bf.resolve().relative_to(root)),tap_target_sinks=1000,tap_max_sinks=1250,tap_radius_um=100)
Q=schema.Plan(plan);rows=taps.density_taps(Q,'native59')
report=dict(scope=a.scope,adopted=False,cycles_added=0,register_sinks=sum(bins.values()),old_ports=len(before),proposed_ports=len(rows),clock=clock,taps=[dict(port=n,x_um=x,y_um=y,sinks=c,max_radius_um=r) for n,x,y,c,r in rows],notes=['Need fresh-kept P3c placed bins; source scope is explicit.','No setup/hold, die clock CPPR, signal+clock GRT or pin/PG gate claimed.','DATA/FT/R8 clocks/833ps unchanged; clock ABI changes require per-die batch.'])
(out/'proposal.json').write_text(json.dumps(report,indent=1)+'\n')
print(json.dumps({k:report[k] for k in ('scope','register_sinks','old_ports','proposed_ports','cycles_added')}))
