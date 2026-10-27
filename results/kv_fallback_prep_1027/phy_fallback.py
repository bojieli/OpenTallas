import json,sys,collections,copy,math
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'tools/die_plan'))
import clock_landing_plan as CP, schema as S, reset_tree as RT
P=json.load(open(R/'pd/hm_r26.json'));T=json.load(open(R/'fallback/wrapper_land_crossings.json'));CP._fill_ft_windows(P,R/'pd/hm_r26.json');CP._fill_port_windows(P,R/'pd/hm_r26.json',T);SP=S.Plan(P,R/'pd/hm_r26.json');W=RT.wf_plan(SP);pr={r['id']:r for r in P['ports']};ins=collections.defaultdict(list)
for r in T['ports']:
 tn=SP.parts[r['dst']]['type']
 if SP.types[tn].get('hard'):ins[tn].append(pr[r['port']])
rows=[]
for tn,prs in ins.items():
 typ=P['partition_types'][tn];used=[];buses={p['dst']['bus']:p for p in prs};entry=CP._reset_entry_xy(W,P,tn);r=dict(type=tn,instances=sum(x['type']==tn for x in P['partitions']),outline_um=typ['outline_um'],reset_entry_um=entry,branches=[])
 for bus,p in sorted(buses.items()):
  point=CP._bus_xy(typ,bus);tree=CP._hard_tree(entry,point);d=dict(bus=bus,width=p['width'],point_um=point,registered_collector=tree)
  try:bank=CP._storage_band(typ,bus,p['width'],used);used.append(bank['rect_um']);d['bank']=bank
  except ValueError as e:d['bank_failure']=str(e)
  r['branches'].append(d)
 r['needed_local_rings']=len(r['branches']);r['collector_plan']='Independent registered reverse chains to the one delivered-reset entry; merge ready by AND and fault by OR at a registered root. Existing generator supports only one chain; extension + proof needed before build.';rows.append(r)
O=R/'fallback';(O/'phy_wrapper_requirements.json').write_text(json.dumps(rows,indent=1)+'\n')
print(json.dumps([dict(type=r['type'],instances=r['instances'],rings=r['needed_local_rings'],storage_failures=sum('bank_failure' in b for b in r['branches']),max_registered_hop=max(b['registered_collector']['max_hop_um'] for b in r['branches'])) for r in rows]))
