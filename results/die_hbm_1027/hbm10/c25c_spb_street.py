"""REJECTED CANDIDATE: exact demand check failed; do not adopt.
Open q_sm2's missing street by moving the adjacent link core into q_spb0 whitespace.
No SM/core-interface/outline/RTL/cycle changes. q_spb0 mirrored placement handles both dies' sides.
usage: c25c_spb_street.py SRC OUT
"""
import hashlib,json,sys
from pathlib import Path
D,O=map(Path,sys.argv[1:3]);O.mkdir(parents=True,exist_ok=True);P=json.load(open(D/'die_plan.json'));t=P['partition_types']['q_spb0'];c=next(c for c in t['hard_cores'] if c['inst']=='u_lk_S0');ox,oy=c['origin_um'];w,h=c['outline_um'];dx,dy=c.get('track_offset_um',[0,0]);delta=34.56
assert ox==0,'street delta assumes the link core is still on boundary'
c['origin_um'][0]=round(ox+delta,4);c['note']=c.get('note','')+' | C25c: move right34.56um to reserve the missing q_sm2 boundary street (SM array unchanged)'
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
 # Unchanged internal station counts; report exact same-count reach before any route.
 pts=[st['from_um']]+st.get('regs_um',[])+[st['to_um']]
 if any('u_lk_S0' in st.get(r,'') for r in ('launch','capture')):
  d=max(sum(abs(x-y) for x,y in zip(a,b)) for a,b in zip(pts,pts[1:]));assert d<=405+1e-6,(st['conn'],d)
(O/'die_plan.json').write_text(json.dumps(P,indent=1)+'\n');r={'source_sha256':hashlib.sha256((D/'die_plan.json').read_bytes()).hexdigest(),'type':'q_spb0','core':'u_lk_S0','old_origin':[ox,oy],'new_origin':c['origin_um'],'reserved_boundary_street_um':34.56,'instances':['NW_spb0','NE_spb0'],'station_updates':updates,'cycles_added':0,'side_clock_tables':'regenerate from composed plan; centre tap moved34.56um with core'};(O/'c25c_spb_street_report.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r,indent=1))
