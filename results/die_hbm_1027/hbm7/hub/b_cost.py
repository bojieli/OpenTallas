"""DIE-HBM-7: tok/s cost of option B (2:1 on <=50%-duty hub links) on the ds S2 schedule (accepted_cost basis).
Run from the repo root: python3 results/die_hbm_1027/hbm7/hub/b_cost.py -> b_cost.json.
Per unit set: latency form (+1 cycle per record) and link-bound form (op time x2)."""
import sys,json
sys.path[:0]=['tools','tools/throughput']
import accepted_cost as AC
from hgi_sim import timing as T
from hgi_sim import ds_native_timing as DT
res=AC.ROOT/'results/arch/hgi_sim_20261010/g25_proof'
d,recs=DT.load(res/'ds_rank0_program.json');recs=T.rebuild_waits(recs)
rg={}
for x in json.loads((res/'ds_full.json').read_text())['results']:
  for s_ in x.get('row_gather') or []: rg[x['layer']]=s_
DT.apply_dyn_counts(recs,rg);cf=DT.NativeCost(d['ops'],recs,row_gather=rg)
def run(units=(),f=1.0,delta=0.0):
  def g(r,dyn,L):
    c=cf(r,dyn,L)
    return (c[0]*f+delta,c[1],c[2]) if r.unit in units else c
  return T.schedule(recs,DT.POS,'S2',cost_fn=g)
o=run();base=o['total_cycles'];out={'base':base,'unit_duty':{u:v['busy']/base for u,v in o['per_unit'].items()}}
for name,units in (('cheap',{'IDX','HC','FUSED'}),('full',{'SU','SM','IDX','HC','FUSED'})):
  for f,dl in ((1.0,1.0),(2.0,0.0)): out[f'{name}_x{f}_+{dl}']=run(units,f,dl)['total_cycles']
for u in ('IDX','HC','FUSED','SU','SM'): out[f'{u}_x2']=run({u},2.0)['total_cycles']
json.dump(out,open('b_cost.json','w'),indent=1)
