import json,sys,collections,re
from pathlib import Path
R=Path(__file__).resolve().parent;sys.path.insert(0,str(R/'tools/die_plan'));import fallback_regions as F,clock_landings as CL
P=json.load(open(R/'pd/hm_r26.json'));parts={p['name']:p for p in P['partitions']};parent={n:n for n in parts};hard={n for n,p in parts.items() if P['partition_types'][p['type']].get('hard')}
def find(n):
 while parent[n]!=n:parent[n]=parent[parent[n]];n=parent[n]
 return n
mission=[]
for p in P['ports']:
 a,b=p['src']['part'],p['dst']['part'];nm=p['src']['bus']+' '+p['dst']['bus']
 if a not in parts or b not in parts or not ({a,b}&hard):continue
 # PHY mission interface clocks with the same-row controller. Reset/FT reset chain is boot-only.
 if p['width']>1 and not re.search('rst|reset|fault|health|boot',nm):parent[find(a)]=find(b);mission.append(p['id'])
reg={n:find(n) for n in parts};_,rect,cl=F.regions(P,0,'partition');lane_of={pr:l['id'] for l in P['lanes'] for pr in l['ports']};rows=[];hard_reset=[]
for p in P['ports']:
 a,b=p['src']['part'],p['dst']['part']
 if a not in reg or b not in reg or reg[a]==reg[b]:continue
 x=dict(port=p['id'],lane=lane_of[p['id']],src=a,dst=b,src_region=reg[a],dst_region=reg[b],width=p['width'],kind=p.get('kind'),added_cycles=3)
 rows.append(x)
 if b in hard:hard_reset.append(dict(x,src_bus=p['src']['bus'],dst_bus=p['dst']['bus'],required_soft_host=next((n for n in parts if n not in hard and reg[n]==reg[b]),None),status='PLAN: relocate boot landing to synchronous neighbouring PC digital wrapper; exact pin/window/netlist and +3boot wavefront offsets pending'))
T=dict(schema='opentallas.fallback_landed.v1',mode='row_local_PHY_PC',regions_count=len(set(reg.values())),regions=[dict(k=i,tag=reg[n],box_um=rect[n],parts=[n]) for i,n in enumerate(sorted(reg))],added_cycles_per_crossing=3,crossings=len(rows),bits=sum(r['width'] for r in rows),ports=rows)
O=R/'fallback';(O/'row_groups_crossings.json').write_text(json.dumps(T,indent=1)+'\n');(O/'row_groups_requirements.json').write_text(json.dumps(CL.requirements(P,T),indent=1)+'\n');(O/'row_groups_phy_reset.json').write_text(json.dumps(hard_reset,indent=1)+'\n')
print('REGIONS',T['regions_count'],'landed',len(rows),'bits',T['bits'],'synchronous_PHY_mission_ports',len(mission),'hard_boot_receivers',len(hard_reset),'missing_soft_host',sum(x['required_soft_host'] is None for x in hard_reset))
