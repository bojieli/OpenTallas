"""Canonical measured source-edge export + shared inv calibration/AOCV; no STA rerun."""
from pathlib import Path
import json,sys,re,hashlib
R=Path(__file__).parent;O=R/'channel_pg_sm3_v2';G=O/'canonical';G.mkdir(exist_ok=True)
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/die_plan');import trial_tap_arrivals as E,die_sta_related as D,clock_components as CC
v=(O/'ctree.v').read_text();(G/'ctree.v').write_text(v);t=json.load(open(O/'tree_frozen.json'))
# Restore the common two-inverter root edge omitted by the prototype's compact
# parent map. It is source-derived, not a topology edit or electrical change.
masters={};drivers={};inputs={}
for m in D._INST_RE.finditer(v):
 pins=dict(D._PIN_RE.findall(m.group(3)))
 if'A'in pins and'Y'in pins:masters[m.group(2)]=m.group(1);drivers[pins['Y']]=m.group(2);inputs[m.group(2)]=pins['A']
parents={n:drivers[net]for n,net in inputs.items()if net in drivers}
assert all(t['parent_of'].get(c,p)==p for c,p in parents.items())
missing={c:p for c,p in parents.items()if c not in t['parent_of']};assert set(missing)=={'b0'} and missing['b0']=='b0_r'
t['parent_of']=parents
for tap in t['taps']:tap['driver']=t['node_buf'][str(tap['node'])]
t['nodes']['0']['region_root']='NW_sm3'
(G/'tree_connected.json').write_text(json.dumps(t,indent=1)+'\n')
parity={}
def pr(n):
 if n not in parity:parity[n]=(pr(parents[n])if n in parents else 0)^int('INV'in masters[n])
 return parity[n]
for n in masters:pr(n)
assert all(pr(tap['driver'])==0 for tap in t['taps'])
D.CPPR_LCA=True;results={}
for C in('TT','FF'):
 lines=['# OT_EDGES v1 source-edge-resolved from measured native output rise/fall; pure inverter tree parity from exact source']
 for l in(O/f'arr_{C}.txt').read_text().splitlines():
  z=l.split();n=z[1];a=list(map(float,z[2:]));lines+=['T '+n+' '+str(a[0])+' '+str(a[1])+' '+str(a[4]),'F '+n+' '+str(a[2])+' '+str(a[3])]
 for l in(O/f'nodes_{C}.txt').read_text().splitlines():
  z=l.split();n=z[1];a=list(map(float,z[2:]));sr=(a[1],a[3])if pr(n)else(a[0],a[2]);sf=(a[0],a[2])if pr(n)else(a[1],a[3]);lines+=['N '+n+' '+' '.join(map(str,sr)),'M '+n+' '+' '.join(map(str,sf))]
 raw=G/f'arr_edges_{C}.txt';raw.write_text('\n'.join(lines)+'\n');a,miss=E.export(G/'tree_connected.json',raw,C,components=True,node_cells=True);assert miss==0
 (G/f'tap_arrivals_{C}.json').write_text(json.dumps(a,indent=1)+'\n');tp={x['port']:x for x in a['taps']};cc,basis=D.resolve_clock_cell('auto',G,a);assert cc=='inv';m,tp=D.apply_clock_cal(a,tp,C,cc,'spice_edge',proof=G)
 region={n:'NW_sm3'for n in tp};lat=250. if C=='TT'else 202.5;ocv=D.clock_ocv_fn('table','shared',m,tp,lat,region=region,clock_cell='inv')
 rows=[]
 for n,x in tp.items():
  for q,y in tp.items():
   if n==q:continue
   lo,hi,os,oh=D.ca_pair_interval(x,y,n,q,m['cppr_node_range_ps'],ocv)
   rows.append(dict(launch=n,capture=q,lo_ps=lo,hi_ps=hi,ocv_setup_ps=os,ocv_hold_ps=oh,common=D.pair_node(x,y)))
 worst=max(rows,key=lambda r:max(abs(r['lo_ps']),abs(r['hi_ps'])))
 res=dict(clock_cell=cc,calibration='spice_edge via clock_components per-master telescoping',shared_droop_region='NW_sm3',AOCV_table=D.APPROVED_AOCV_TABLE,parent_core_latency_budget_ps=lat,calibrated_late_window_ps=max(x['late_ps']for x in tp.values())-min(x['late_ps']for x in tp.values()),calibrated_early_window_ps=max(x['early_ps']for x in tp.values())-min(x['early_ps']for x in tp.values()),worst_related_interval_abs_ps=max(abs(worst['lo_ps']),abs(worst['hi_ps'])),worst_pair=worst,pairs=len(rows),complete_measured_components=a['clock_components_basis'],root_parent_inventory_repair=missing,added_clock_scale=1.,signed_native_core_views=False)
 results[C]=res
 (G/f'calibrated_{C}.json').write_text(json.dumps(dict(meta=m,taps=list(tp.values()),pairs=rows),indent=1)+'\n')
(G/'qualification.json').write_text(json.dumps(results,indent=1)+'\n');print(json.dumps(results,indent=1))
