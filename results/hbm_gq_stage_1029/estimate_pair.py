import json,math,hashlib
from pathlib import Path
p=Path('/srv/opentallas-scratch/claude/codex-hbm-1028/c25c_native');d=json.loads((p/'die_plan.json').read_text());rows=[]
for typ in ['q_hub_ne','q_hub_nw']:
 t=d['partition_types'][typ];g=next(c for c in t['hard_cores']if c['inst']=='u_hcollgi_Q__q1');ring=next(c for c in t['hard_cores']if c['inst']=='u_hb_coll_Q_ring_ag__q1');gp=json.loads(next(Path('/srv/opentallas-scratch/claude/hbm-gq-stage-1029/spread/cores').glob('*.json')).read_text());gp={r['name']:r for r in gp};rp={r['name']:r for r in json.loads((p/ring['pins_file']).read_text())};cand=[]
 for ix in range(-8,70):
  for iy in range(-35,45):
   x=round(g['origin_um'][0]+237.6+4.32+ix*8.64,3);y=round(g['origin_um'][1]+iy*8.64,3);w,h=ring['outline_um'];reach=max(abs(g['origin_um'][0]+gp['ra_lp_data[%d]'%k]['x']-x-rp['ra_lp_data[%d]'%k]['x'])+abs(g['origin_um'][1]+gp['ra_lp_data[%d]'%k]['y']-y-h+rp['ra_lp_data[%d]'%k]['y'])for k in range(256))
   if reach>405:continue
   coll=[]
   for c in t['hard_cores']:
    if c['inst']==ring['inst']:continue
    cx,cy=c['origin_um'];cw,ch=c['outline_um'];halo=4.32
    if x<cx+cw+halo and x+w+halo>cx and y<cy+ch+halo and y+h+halo>cy:coll.append(c['inst'])
   st=[]
   for si,s in enumerate(t.get('internal_stations',[])):
    for pi,(sx,sy) in enumerate(s.get('regs_um',[])):
     if x-4.32<=sx<=x+w+4.32 and y-4.32<=sy<=y+h+4.32:st.append([si,pi,s.get('conn')])
   cand.append(dict(origin_um=[x,y],max_direct_reach_um=round(reach,3),hard_collisions=coll,station_centres_inside=st))
 cand.sort(key=lambda c:(len(c['hard_collisions']),len(c['station_centres_inside']),c['max_direct_reach_um']));rows.append(dict(type=typ,source_fixed_origin=g['origin_um'],geometrically_reachable_candidates=len(cand),zero_hard_collision=sum(not c['hard_collisions']for c in cand),best=cand[:8]))
r=dict(status='ESTIMATE only; existing native hardlot+stationcentres; station extents absent, no actual station realization, no adoption',base_plan_sha256=hashlib.sha256((p/'die_plan.json').read_bytes()).hexdigest(),method='GQ fixed; ring R0->MX unchanged,8.64 origin grid, all256 exact pins,4.32 hardlot clearance; existing station centre+4.32 exclusion only',rows=rows)
Path('/srv/opentallas-scratch/claude/hbm-gq-stage-1029/packet/gq_ring_pair_estimate.json').write_text(json.dumps(r,indent=1));print(json.dumps(r,indent=1)[:7000])
