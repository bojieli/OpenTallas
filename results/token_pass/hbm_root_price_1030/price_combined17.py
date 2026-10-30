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
def run(shell=False,wide=False):
 def cost(r,dyn,L):
  c=cf(r,dyn,L);t=c[0]
  if r.unit=='COLL':t+=(34+(32 if r.op in REDUCE else 17))*(2 if r.op in CROSS2 else 1)
  t+={'IDX':31,'SU':3}.get(r.unit,0)
  if shell and r.unit=='FUSED':t+={'HC_PRE_NORM':48,'HC_POST':32}.get(r.op,0)
  if shell and r.unit=='COLL':t+=17*(2 if r.op in CROSS2 else 1)
  elif shell and wide and r.unit in {'SM','HC','FUSED','IDX','SU','SFU','ATT','ARGMAX','DMA'}:t+=12
  return t,c[1],c[2]
 return T.schedule(recs,DT.POS,'S2',cost_fn=cost)['total_cycles']
reference=run();assert abs(reference-610734.931155155)<.1,reference
print('REFERENCE',reference,flush=True)
rows=[]
for name,wide in [('N1_tnode_plus_Southern_COLL_pair17_perphase',False)]:
 t=run(True,wide);base=576702.4178
 row=dict(case=name,cycles=t,added_cycles=t-reference,tok_s=1906*base/t,loss_vs_record_pct=100*(1-reference/t),loss_vs_1812_4_pct=100*(1-(1906*base/t)/1812.4));rows.append(row);print(json.dumps(row),flush=True)
out=dict(scope='SEAM_PIN_GEOMETRY_REPAIR_PAIR17_ASSUMED_SOUTHERN_EXPOSURE_S2_SENSITIVITY',source_commit='TO_BE_PINNED',reference_cycles=reference,native_counts={op+'/N'+str(n):cnt for(op,n),cnt in native_counts.items()},rows=rows,rate_excludes_native_VM_spill_DMAS_fences_drains=True,multiuser_ROWX_programme_priced=False,Northern_paths_actually_unchanged=True,all_COLLandVM_exposure_only_assumed=True)
Path(sys.argv[1]).write_text(json.dumps(out,indent=2)+'\n')
