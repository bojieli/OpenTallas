"""Tnode external physical-face shell only, scoped nativeS2N1 sensitivity.
Measured source tree levels4 times input+1/output+1 yields RT+16.
At unchanged row pace, HC_POST+32 and HC_PRE+48; no hub-detour cost here.
Exact selected legacy S2 records contain no ROWX extension. N is not inferred
from vector dimension5120, MDesc.m or other tensor shape. Multiuser native
ROWX programmes require independent source mapping and are not priced here.
All native VM spill/DMA/drain/whole-programme exclusions remain.
"""
import sys,json,hashlib
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/throughput')]
import accepted_cost as AC
from hgi_sim import timing as T
from hgi_sim import ds_native_timing as DT
res=ROOT/'results/arch/hgi_sim_20261010/g25_proof'
d,recs=DT.load(res/'ds_rank0_program.json');recs=T.rebuild_waits(recs)
rg={}
for x in json.loads((res/'ds_full.json').read_text())['results']:
 for st in x.get('row_gather')or[]:rg[x['layer']]=st
DT.apply_dyn_counts(recs,rg);cf=DT.NativeCost(d['ops'],recs,row_gather=rg)

from hgi_sim.records import decode_one
native_counts=Counter()
for layer in d['layers']:
 for item in layer['records']:
  raw=bytes.fromhex(item['hex']);r,end=decode_one(raw,0)
  if r.unit=='FUSED'and r.op in ('HC_PRE_NORM','HC_POST'):
   if end!=len(raw)or r.encode()!=raw:raise ValueError('native row extension/unparsed source requires explicit ROWX N authority')
   native_counts[(r.op,1)]+=1
assert native_counts=={('HC_PRE_NORM',1):81,('HC_POST',1):80},native_counts
CROSS2=('ALL_REDUCE_SUM','GROUP_REDUCE_MCAST');REDUCE=CROSS2+('TOPK_MERGE','ARGMAX_MERGE')
def run(shell=False):
 def cost(r,dyn,L):
  c=cf(r,dyn,L);t=c[0]
  if r.unit=='COLL':t+=(34+(32 if r.op in REDUCE else 17))*(2 if r.op in CROSS2 else 1)
  t+={'IDX':31,'SU':3}.get(r.unit,0)
  if shell and r.unit=='FUSED':t+={'HC_PRE_NORM':48,'HC_POST':32}.get(r.op,0)
  return t,c[1],c[2]
 return T.schedule(recs,DT.POS,'S2',cost_fn=cost)['total_cycles']
reference=run();assert abs(reference-610734.931155155)<.1,reference
print('REFERENCE',reference,flush=True)
t=run(True);base=576702.4178
out=dict(scope='TNODE_ONLY_SINGLE_POSITION_N1_NATIVE_S2_SENSITIVITY_NOT_G5',source_commit='TO_BE_PINNED',reference_cycles=reference,cycles=t,added_cycles=t-reference,reference_tok_s=1906*base/reference,tok_s=1906*base/t,loss_vs_record_pct=100*(1-reference/t),loss_vs_1812_4_pct=100*(1-(1906*base/t)/1812.4),native_N_authority='fused_job217_emit.py n=rx.n if ROWX else 1; selected g25 codec consumes entire nativebase record and reencodes exactly, no appended ROWX',native_counts={op+'/N'+str(n):cnt for(op,n),cnt in native_counts.items()},per_record_extra_cycles={'HC_PRE_NORM/N1':48,'HC_POST/N1':32},QDQ_extra_cycles=0,external_tree_levels=4,input_shell_stages=1,output_shell_stages=1,root_roundtrip_added_cycles=16,row_pace_added_cycles=0,hub_detour_added_cycles=0,rate_excludes_native_VM_spill_and_drains=True,multiuser_ROWX_programme_priced=False)
Path(sys.argv[1]).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
