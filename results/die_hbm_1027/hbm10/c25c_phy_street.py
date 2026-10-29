"""Open q_sm2's missing street by moving the complete adjacent PHY/PG/halo tuple into q_spb0 whitespace.
No SM/core-interface/outline/RTL/cycle changes. PHY placement shifts103.68um, preserving63.64um PG halo and>=34.56umstreet. q_spb0 mirrored placement handles both dies' sides.
usage: c25c_phy_street.py SRC OUT
"""
import hashlib,json,sys
from pathlib import Path
D,O=map(Path,sys.argv[1:3]);O.mkdir(parents=True,exist_ok=True);P=json.load(open(D/'die_plan.json'));t=P['partition_types']['q_spb0'];c=next(c for c in t['hard_cores'] if c['inst']=='u_lk_S0');ox,oy=c['origin_um'];w,h=c['outline_um'];dx,dy=c.get('track_offset_um',[0,0]);delta=103.68
assert ox==0,'street delta assumes the link core is still on boundary'
c['origin_um'][0]=round(ox+delta,4);c['note']=c.get('note','')+' | C25c: move right103.68um to reserve the missing q_sm2 boundary street (SM array unchanged)'
for q in t['hard_cores']:
 if q is c:continue
 x,y=q['origin_um'];qw,qh=q['outline_um'];assert not(c['origin_um'][0]<x+qw-1e-6 and x<c['origin_um'][0]+w-1e-6 and oy<y+qh-1e-6 and y<oy+h-1e-6)
for q in t.get('contents',[]):
 if q['inst']=='u_lk_S0':q['origin_um'][0]=round(q['origin_um'][0]+delta,4)
for q in t.get('clock',{}).get('taps',[]):
 if q['name'].split('.')[0]=='u_lk_S0':q['xy'][0]=round(q['xy'][0]+delta,4)
updates=[]
for st in t.get('internal_stations',[]):
 for endpoint,ref in (('from_um','launch'),('to_um','capture')):
  if not st.get(ref,'').startswith('u_lk_S0'):continue
  a=st[endpoint]
  if ox+dx-1<=a[0]<=ox+dx+w+1 and oy+dy-1<=a[1]<=oy+dy+h+1:st[endpoint]=[round(a[0]+delta,4),a[1]];updates.append({'conn':st['conn'],'endpoint':endpoint,'before':a,'after':st[endpoint]})
 # If a changed endpoint consumes its margin, resite its existing end relay in free lattice rows.
 def dist(a,b):return sum(abs(x-y) for x,y in zip(a,b))
 regs=st.get('regs_um',[])
 if regs:
  for idx in (0,len(regs)-1):
   q=regs[idx];left=st['from_um'] if idx==0 else regs[idx-1];right=st['to_um'] if idx==len(regs)-1 else regs[idx+1]
   if max(dist(left,q),dist(q,right))<=405:continue
   cand=[]
   for ix in range(-16,17):
    for iy in range(-16,17):
     z=[round(q[0]+ix*8.64,4),round(q[1]+iy*8.64,4)]
     if max(dist(left,z),dist(z,right))>405:continue
     if any(cc['origin_um'][0]-.5<=z[0]<=cc['origin_um'][0]+cc['outline_um'][0]+.5 and cc['origin_um'][1]-.5<=z[1]<=cc['origin_um'][1]+cc['outline_um'][1]+.5 for cc in t['hard_cores']):continue
     cand.append((dist(q,z),z))
   assert cand,(st['conn'],'no endpoint relay site');z=min(cand)[1];updates.append({'conn':st['conn'],'relay':idx,'before':q,'after':z});regs[idx]=z
 # Unchanged internal station counts; report exact same-count reach before any route.
 pts=[st['from_um']]+st.get('regs_um',[])+[st['to_um']]
 if any('u_lk_S0' in st.get(r,'') for r in ('launch','capture')):
  d=max(sum(abs(x-y) for x,y in zip(a,b)) for a,b in zip(pts,pts[1:]));assert d<=405+1e-6,(st['conn'],d)
# Move the complete PHY/halo/PG-window tuple, not just its digital abstract.
assert t['clock']['keepouts_um']==[[0.0,0.0,663.688,1113.64],[0.0,0.0,600.048,1050.0]]
t['clock']['keepouts_um']=[[69.12,0.0,767.368,1113.64],[103.68,0.0,703.728,1050.0]]
sm=P['partition_types']['q_sm2']['clock']['keepouts_um'];oldclip=[5771.52,0.0,5806.08,1113.64];assert oldclip in sm;sm.remove(oldclip)
for io in P['die']['io']:
 if io['name'] in ('io_NW_spb0_u_lk_S0','io_NE_spb0_u_lk_S0'):
  dd=delta if io['name'].startswith('io_NW') else -delta
  io['rect_um']=[round(v+(dd if k in (0,2) else 0),4) for k,v in enumerate(io['rect_um'])]
for domain in P['die']['pg']['domains']:
 if domain['name'] in ('phy_NW_spb0_u_lk_S0','phy_NE_spb0_u_lk_S0'):
  dd=delta if domain['name'].startswith('phy_NW') else -delta
  domain['rect_um']=[round(v+(dd if k in (0,2) else 0),4) for k,v in enumerate(domain['rect_um'])]
  domain['bumps']['rect_um']=[round(v+(dd if k in (0,2) else 0),4) for k,v in enumerate(domain['bumps']['rect_um'])]
(O/'die_plan.json').write_text(json.dumps(P,indent=1)+'\n');r={'source_sha256':hashlib.sha256((D/'die_plan.json').read_bytes()).hexdigest(),'type':'q_spb0','core':'u_lk_S0','old_origin':[ox,oy],'new_origin':c['origin_um'],'reserved_boundary_street_um':40.04,'phy_shift_um':103.68,'pg_margin_um':63.64,'requires':'PG solve + full G0 and core-station physical PHY access review before route','instances':['NW_spb0','NE_spb0'],'station_updates':updates,'cycles_added':0,'side_clock_tables':'regenerate from composed plan; centre tap moved34.56um with core'};(O/'c25c_spb_street_report.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1))
