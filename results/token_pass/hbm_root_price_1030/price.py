"""HBM root detour conditional price on accepted DS native S2 model.
Data L4/L4m both11 -> NWtoNE18(+7), NEtoNW16(+5).
Control L96/L96m both12 ->18/16(+6/+4). Exact pair receipt retained.
Rate EXCLUDES current native VM spill bytes, finite-phase DMA/fence/drain cost.
HCOL is COLL-family; VMS bus accesses span multiple memory unit families and
lack current relocated per-record bank/crossing authority, so wide rows are
sensitivities, never measured rates or adoption claims.
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
REDUCE=('ALL_REDUCE_SUM','GROUP_REDUCE_MCAST');OPSRED=REDUCE+('TOPK_MERGE','ARGMAX_MERGE')
def cross(r):return 2 if r.op in REDUCE else 1
MEMUNITS={'SM','HC','FUSED','IDX','SU','SFU','ATT','ARGMAX','DMA','COLL'}
def run(detour=None):
 def cost(r,dyn,L):
  c=cf(r,dyn,L);t=c[0]
  if r.unit=='COLL':t+=(34+(32 if r.op in OPSRED else 17))*cross(r)
  t+={'IDX':31,'SU':3}.get(r.unit,0)
  if detour:t+=detour(r)
  return t,c[1],c[2]
 return T.schedule(recs,DT.POS,'S2',cost_fn=cost)['total_cycles']
def clean():return T.schedule(recs,DT.POS,'S2',cost_fn=cf)['total_cycles']
base=clean();assert abs(base-576702.4178)<.1,base
record=run();rate=lambda t:1906*base/t
cases=[('COLL_ne_to_nw_data5_once',lambda r:5 if r.unit=='COLL'else 0),
 ('COLL_nw_to_ne_data7_once',lambda r:7 if r.unit=='COLL'else 0),
 ('COLL_pair_data12_once',lambda r:12 if r.unit=='COLL'else 0),
 ('COLL_data7_per_cross_phase',lambda r:7*cross(r)if r.unit=='COLL'else 0),
 ('COLL_pair_data12_per_cross_phase',lambda r:12*cross(r)if r.unit=='COLL'else 0),
 ('COLL_pair_control10_once',lambda r:10 if r.unit=='COLL'else 0),
 ('COLL_AG_only_pair12',lambda r:12 if r.unit=='COLL'and r.op=='ALL_GATHER'else 0),
 ('wide_all_VM_units_pair12_once',lambda r:12 if r.unit in MEMUNITS else 0),
 ('wide_nonCOLL_VM_pair12_plus_COLL_pair12_perphase',lambda r:12*cross(r)if r.unit=='COLL'else 12 if r.unit in MEMUNITS else 0)]
# Keyword spacing explicit: expression parser should reject accidental else 0.
rows=[]
for name,fn in cases:
 t=run(fn);r=dict(case=name,cycles=t,tok_s=rate(t),delta_cycles=t-record,loss_vs_record_pct=100*(1-record/t),loss_vs_1812_4_pct=100*(1-rate(t)/1812.4));rows.append(r);print(json.dumps(r),flush=True)
out=dict(scope='PLAN_ONLY_CONDITIONAL_S2_BOUNDS_NOT_MEASURED_RATE',base_cycles=base,current_record_cycles=record,current_record_tok_s=rate(record),rate_excludes_native_VM_spill_bytes=True,rate_excludes_native_VM_serialization_drains=True,records_per_unit=dict(Counter(r.unit for r in recs)),COLL_ops=dict(Counter(r.op for r in recs if r.unit=='COLL')),COLL_families=dict(Counter(r.family for r in recs if r.unit=='COLL')),rows=rows)
Path(sys.argv[1]).write_text(json.dumps(out,indent=2)+'\n')
