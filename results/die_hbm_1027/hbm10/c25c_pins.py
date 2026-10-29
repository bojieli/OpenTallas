"""C25c bdring shape and QW decoder face utilisation. No RTL or cycle change.
usage: c25c_pins.py SRC_DIR OUT_DIR
OUT overlays SRC: copy other side files before composing into a standalone plan.
"""
import argparse, copy, hashlib, json, math
from pathlib import Path

def snap(v): return round(.024 + round((v-.024)/.048)*.048, 4)
def face(p,w,h):
 x,y=p['x'],p['y']; d,f=min((x,'W'),(w-x,'E'),(y,'S'),(h-y,'N'))
 return f if d<1 else 'I'
def orient(x,y,w,h,o):
 if o in ('MY','R180'): x=w-x
 if o in ('MX','R180'): y=h-y
 return x,y

def main(src,out,bdring_split=False):
 src,out=Path(src),Path(out);out.mkdir(parents=True,exist_ok=True);(out/'cores').mkdir(exist_ok=True)
 raw=(src/'die_plan.json').read_bytes();p=json.loads(raw)
 report={'source_sha256':hashlib.sha256(raw).hexdigest(),'cycles_added':0,'changes':[],'endpoint_reach':[]}
 mods={'ot_hgi_sm_xload_cl2_bdring':(120.96,216.),'ot_hgi_qw_dec':(260.,260.)}
 for mod,(nw,nh) in mods.items():
  users=[(tn,t,c) for tn,t in p['partition_types'].items() for c in t.get('hard_cores',[]) if c['module']==mod]
  ow,oh=users[0][2]['outline_um']; files={c['pins_file'] for _,_,c in users};assert len(files)==1
  oldpins=json.loads((src/next(iter(files))).read_text());pins=copy.deepcopy(oldpins)
  groups={f:[q for q in pins if face(q,ow,oh)==f] for f in 'WENSI'}
  if mod.endswith('bdring'):
   assert abs(nw*nh-ow*oh)<1e-6
   for f in ('W','E'):
    qs=sorted(groups[f],key=lambda q:(q['y'],q['name']));pitch=.096 if f=='W' else .288
    start=snap((nh-(len(qs)-1)*pitch)/2)
    for i,q in enumerate(qs):q.update(x=.096 if f=='W' else round(nw-.096,4),y=round(start+i*pitch,4))
   for q in groups['I']:q.update(x=round(q['x']+(nw-ow)/2,4),y=round(q['y']+(nh-oh)/2,4))
   if bdring_split:
    # Common-master face census proves local S faces every bq_d partner; retain half on W for capacity.
    bq=sorted(groups['W'],key=lambda q:int(q['name'].split('[')[1].rstrip(']')))
    assert len(bq)==2048 and all(q['name'].startswith('bq_d[') for q in bq)
    for i,q in enumerate(bq[:1024]):q.update(layer='M4',x=.096,y=round(snap((nh-1023*.192)/2)+i*.192,4))
    for i,q in enumerate(bq[1024:]):q.update(layer='M5',x=round(snap((nw-1023*.096)/2)+i*.096,4),y=.096)

  else:
   for f in ('S','E'):
    reserved=[q for q in groups[f] if q['name']=='clk'];qs=sorted([q for q in groups[f] if q['name']!='clk'],key=lambda q:(q['x' if f=='S' else 'y'],q['name']))
    axis='x' if f=='S' else 'y'; rpos=[q[axis] for q in reserved]
    positions=[snap(5+i*250/(len(qs)-1)) for i in range(len(qs))]
    for i,v in enumerate(positions):
     if any(abs(v-r)<.096-1e-6 for r in rpos):
      choices=[snap(v+d*.048) for d in (-2,-1,1,2)]
      v=next(v2 for v2 in choices if all(abs(v2-r)>=.096-1e-6 for r in rpos) and (i==0 or v2-positions[i-1]>=.096-1e-6) and (i==len(qs)-1 or positions[i+1]-v2>=.096-1e-6))
     positions[i]=v
    for q,v in zip(qs,positions):q[axis]=v
  assert {q['name'] for q in pins}=={q['name'] for q in oldpins}
  pf=f'cores/{mod}__{nw:g}x{nh:g}__c25c.json';(out/pf).write_text(json.dumps(pins,indent=1)+'\n')
  spans={}
  for f in ('W','E','N','S'):
   qs=[q for q in pins if face(q,nw,nh)==f]
   if qs:
    axis='y' if f in 'WE' else 'x';pos=sorted(q[axis] for q in qs)
    spans[f]={'pins':len(qs),'span_um':round(pos[-1]-pos[0],4),'fraction':round((pos[-1]-pos[0])/(nh if f in 'WE' else nw),4),'min_pitch_um':round(min(b-a for a,b in zip(pos,pos[1:])),4) if len(pos)>1 else None}
  rows=[]
  for tn,t,c in users:
   ox,oy=c['origin_um'];dx,dy=c.get('track_offset_um',[0,0]);nx,ny=round(ox+(ow-nw)/2,4),round(oy+(oh-nh)/2,4);o=c.get('orient','R0')
   # Pin exact-coordinate endpoint map plus geometric face endpoints used by aggregate bus stations.
   pm={}
   for a,b in zip(oldpins,pins):
    ax,ay=orient(a['x'],a['y'],ow,oh,o);bx,by=orient(b['x'],b['y'],nw,nh,o)
    pm[(round(ox+dx+ax,4),round(oy+dy+ay,4))]=[round(nx+dx+bx,4),round(ny+dy+by,4)]
   moved=0
   for s in t.get('internal_stations',[]):
    for key,ref in (('from_um','launch'),('to_um','capture')):
     if not s.get(ref,'').startswith(c['inst']):continue
     xy=s.get(key)
     if not xy:continue
     k=tuple(round(v,4) for v in xy)
     if k in pm:s[key]=pm[k];moved+=1
     elif ow!=nw or oh!=nh:
      x,y=xy
      if ox+dx-1<=x<=ox+dx+ow+1 and oy+dy-1<=y<=oy+dy+oh+1:
       s[key]=[round(nx+dx+(x-ox-dx)*nw/ow,4),round(ny+dy+(y-oy-dy)*nh/oh,4)];moved+=1
   c.update(origin_um=[nx,ny],outline_um=[nw,nh],pins_file=pf)
   if ow!=nw or oh!=nh:
    c.pop('lef',None);c.pop('lib',None)
   c['note']=c.get('note','')+' | C25c: same-area aspect repair, centre clock unchanged' if mod.endswith('bdring') else c.get('note','')+' | C25c: E/S pins spread across full face; clock unchanged'
   for ct in t.get('contents',[]):
    if ct.get('inst')==c['inst']:ct.update(origin_um=[nx,ny],outline_um=[nw,nh])
   # Shapes are centre-anchored; clock taps remain at their exact original global coordinates.
   hits=[]
   for q in t['hard_cores']:
    if q is c:continue
    qx,qy=q['origin_um'];qx+=q.get('track_offset_um',[0,0])[0];qy+=q.get('track_offset_um',[0,0])[1];qw,qh=q['outline_um']
    if nx+dx<qx+qw-1e-6 and qx<nx+dx+nw-1e-6 and ny+dy<qy+qh-1e-6 and qy<ny+dy+nh-1e-6:hits.append(q['inst'])
   assert not hits,(tn,c['inst'],hits)
   rows.append({'type':tn,'inst':c['inst'],'origin_um':[nx,ny],'station_endpoints_updated':moved,'overlaps':hits})
  report['changes'].append({'module':mod,'outline_before':[ow,oh],'outline_after':[nw,nh],'pins':len(pins),'face_spans':spans,'users':rows})
 # Repair only endpoint relay positions where the outline change consumes the existing reach margin.
 def dist(a,b):return sum(abs(x-y) for x,y in zip(a,b))
 for tn,t in p['partition_types'].items():
  for st in t.get('internal_stations',[]):
   if not any(k in str(st.get('launch',''))+str(st.get('capture','')) for k in ('u_xq_Q_p0_bd','u_xq_Q_p1_bd','u_hb_quant_Q__u_dec')):continue
   regs=st.get('regs_um',[]);pts=[st['from_um']]+regs+[st['to_um']]
   before=max(dist(a,b) for a,b in zip(pts,pts[1:]))
   if before>405 and regs:
    for idx in (0,len(regs)-1):
     q=regs[idx];left=st['from_um'] if idx==0 else regs[idx-1];right=st['to_um'] if idx==len(regs)-1 else regs[idx+1]
     if max(dist(left,q),dist(q,right))<=405:continue
     candidates=[]
     for ix in range(-12,13):
      for iy in range(-12,13):
       xy=[round(q[0]+ix*8.64,4),round(q[1]+iy*8.64,4)]
       if max(dist(left,xy),dist(xy,right))>405:continue
       if any(c['origin_um'][0]+c.get('track_offset_um',[0,0])[0]-.5<=xy[0]<=c['origin_um'][0]+c.get('track_offset_um',[0,0])[0]+c['outline_um'][0]+.5 and c['origin_um'][1]+c.get('track_offset_um',[0,0])[1]-.5<=xy[1]<=c['origin_um'][1]+c.get('track_offset_um',[0,0])[1]+c['outline_um'][1]+.5 for c in t.get('hard_cores',[])):continue
       candidates.append((dist(q,xy),max(dist(left,xy),dist(xy,right)),xy))
     assert candidates,(tn,st['conn'],'no same-count endpoint repair')
     xy=min(candidates)[2];report['endpoint_reach'].append({'type':tn,'conn':st['conn'],'register_index':idx,'before_um':q[:],'after_um':xy})
     regs[idx]=xy
   pts=[st['from_um']]+regs+[st['to_um']];after=max(dist(a,b) for a,b in zip(pts,pts[1:]))
   assert after<=405+1e-6,(tn,st['conn'],after)
   report.setdefault('reach_census',[]).append({'type':tn,'conn':st['conn'],'max_hop_um':round(after,4),'registers':len(regs)})
 (out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n')
 report['plan_sha256']=hashlib.sha256((out/'die_plan.json').read_bytes()).hexdigest()
 (out/'c25c_pins_report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report,indent=1))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('src');ap.add_argument('out');ap.add_argument('--bdring-split',action='store_true');a=ap.parse_args();main(a.src,a.out,a.bdring_split)
