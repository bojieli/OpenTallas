import json,sys,copy,hashlib
from pathlib import Path
import numpy as np
W=Path('/srv/opentallas-scratch2/claude/wt/codex-hbm-stations-1101');sys.path.insert(0,str(W/'tools/die_plan'));import schema as S
from gen_phys import type_pins
B=Path('/srv/opentallas-scratch2/claude');r=B/'codex-hbm-stations-1101';canonical=r/'base.json';old=json.load(open(canonical));p=copy.deepcopy(old);patch=[];audit=[];groups={}
selections=[('rootstations',8),('lanestations',18),('stations',4),('freestations',5),('b101stations-n1',2),('finalstations-n1',1)]
seen=set()
for kind,count in selections:
 d=B/('codex-hbm-'+kind+'-1101');small=kind=='stations';j=json.load(open(d/('small_representative_plan.json' if small else 'representative_plan.json')));led=json.load(open(d/('small_ledger.json' if small else 'ledger.json')));rs=[x for x in led if x.get('status','PASS')=='PASS'];assert len(rs)==count,(kind,len(rs));model=S.Plan(j,None)
 for row in rs:
  tn,name=row['type'],row['slot'];assert (tn,name) not in seen;seen.add((tn,name));a=next(x for x in old['partition_types'][tn]['ft_slots'] if x['name']==name);b=next(x for x in j['partition_types'][tn]['ft_slots'] if x['name']==name);changed={k for k in set(a)|set(b) if a.get(k)!=b.get(k)};assert changed<={'stations','regs_um','bit_sites_um','bit_site_cell_um','note'},changed
  dest=next(x for x in p['partition_types'][tn]['ft_slots'] if x['name']==name)
  for k in changed:dest[k]=b[k]
  pins={(bn,i):(x,y) for bn,i,l,x,y,f in type_pins(model,tn)};n=b['width']+1;aa=np.array([pins[(name+'_i',i)] for i in range(n)]);bb=np.array([pins[(name+'_o',i)] for i in range(n)]);ss=np.array(b['bit_sites_um'])+np.array(b['bit_site_cell_um'])/2;h=[float(abs(y-x).sum(1).max()) for x,y in zip([aa]+list(ss),list(ss)+[bb])];assert max(h)<=403.00001,(tn,name,h)
  patch.append(dict(type=tn,slot=name,old_stations=a['stations'],new_stations=b['stations'],added_cycles=b['stations']-a['stations'],replace={k:b[k] for k in changed}));audit.append(dict(type=tn,slot=name,source=kind,hops_um=h,max_hop_um=max(h),added_cycles=b['stations']-a['stations']));groups.setdefault(tn,{})[name]=dict(bit_site_cell_um=b['bit_site_cell_um'],bit_sites_um=b['bit_sites_um'])
assert len(patch)==38
a,b=S.Plan(old,None),S.Plan(p,None);cycles=[]
for lid in a.lanes:
 aa,bb=a.lane_latency(lid),b.lane_latency(lid)
 if aa!=bb:cycles.append(dict(lane=lid,old=aa,new=bb,added_cycles=bb['cycles']-aa['cycles'],added_natural_cycles=bb['natural']-aa['natural']))
latency_rows={}
for row in cycles:
 lid=row['lane'];item=copy.deepcopy(old['latency']['lanes'][lid]);item.update(row['new']);latency_rows[lid]=item
r8=[]
for group in old.get('latency_groups',[]):
 if any(x['lane'] in group['lanes'] for x in cycles):
  r8.append(dict(name=group['name'],kind=group.get('kind'),members=[dict(lane=lid,old=a.lane_latency(lid),new=b.lane_latency(lid)) for lid in group['lanes']]))
mirrors=[]
for row in cycles:
 lid=row['lane']
 if lid+'m' in a.lanes:
  aa,bb=a.lane_latency(lid+'m'),b.lane_latency(lid+'m')
  mirrors.append(dict(lane=lid,mirror=lid+'m',added_natural_cycles=row['added_natural_cycles'],mirror_added_natural_cycles=bb['natural']-aa['natural'],added_cycles=row['added_cycles'],mirror_added_cycles=bb['cycles']-aa['cycles']))
price=dict(schema='opentallas.hbm_station_tok_price.v1',status='CANDIDATE_NOT_ADOPTED',period_ps=833,aggregate_token_rate='NOT CLAIMED: caller must compose traversals in its schedule',lanes=[dict(lane=x['lane'],ports=a.lanes[x['lane']].get('ports',[]),param=old['latency']['lanes'][x['lane']].get('param'),old_cycles=x['old']['cycles'],new_cycles=x['new']['cycles'],added_cycles=x['added_cycles'],added_natural_cycles=x['added_natural_cycles'],old_pad=x['old']['pad'],new_pad=x['new']['pad'],extra_ps_per_traversal=833*x['added_cycles']) for x in cycles])
p['latency']['lanes'].update(latency_rows)
result=dict(schema='opentallas.hbm_station_repair_patch.v1',status='COMPOSE_CANDIDATE_NOT_ROUTED',source_plan_sha256=hashlib.sha256(canonical.read_bytes()).hexdigest(),patches=patch,cycle_impact=cycles,replace_latency_lanes=latency_rows,r8_group_impact=r8,mirror_impact=mirrors,tok_model_price=price)
outputs={'selected_patch.json':result,'selected_plan.json':p,'selected_ledger.json':audit,'tok_model_price.json':price,'latency_table_delta.json':dict(lanes=latency_rows),'reservations.json':dict(schema='opentallas.hbm_selected_station_reservations.v1',status='COMPOSE_CANDIDATES_NOT_ROUTED',selected_slot_count=38,types=groups)}
for name,obj in outputs.items():
 out=r/name;tmp=r/(name+'.tmp');tmp.write_text(json.dumps(obj,separators=(',',':')));tmp.replace(out)
print('slots',len(patch),'zero',sum(x['added_cycles']==0 for x in patch),'cells',sum(len(st) for t in groups.values() for s in t.values() for st in s['bit_sites_um']))
print(json.dumps(price,indent=2));print('R8',json.dumps(r8))
review=[];model=S.Plan(p,None)
for rec in audit:
 tn,sl=rec['type'],rec['slot'];t=model.types[tn];s=next(x for x in t['ft_slots'] if x['name']==sl);pins={(bn,i):(x,y) for bn,i,l,x,y,f in type_pins(model,tn)};n=s['width']+1
 review.append(dict(type=tn,slot=sl,source=rec['source'],outline=t['outline_um'],boxes=list(S.placed_macro_boxes(t).values()),a=[pins[(sl+'_i',i)] for i in range(n)],b=[pins[(sl+'_o',i)] for i in range(n)],sites=(np.array(s['bit_sites_um'])+np.array(s['bit_site_cell_um'])/2).tolist(),new_regs=s['regs_um'],hops=rec['hops_um'],added_cycles=rec['added_cycles']))
(r/'selected_review_data.json').write_text(json.dumps(review,separators=(',',':')))
