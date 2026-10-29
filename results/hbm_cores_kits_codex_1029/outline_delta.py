#!/usr/bin/env python3
"""Two opt-in HBM outline fixes from measured congestion/pin/macro failures.
Never routes. Resite stations and rebuild die/clock before adoption.
"""
import copy,json,math,os,shutil,sys
from pathlib import Path
base,out=map(Path,sys.argv[1:3]);variant=int(sys.argv[3]);out.mkdir(parents=True,exist_ok=False)
d=json.load(open(base/'die_plan.json'));cm=json.load(open(base/'core_macros.json'));ce=json.load(open(base/'clock_entries.json'))
variants={
'ot_hbm_su_static_qcore_r13':[[293.76,207.36],[224.64,276.48]],
'ot_hbm_su_static_cxport_ij_q':[[362.88,388.8],[380.16,362.88]],
'ot_hbm_su_static_sfustore_hw':[[362.88,388.8],[475.2,267.84]]}
def box(c):x,y=c['origin_um'];w,h=c['outline_um'];return[x,y,x+w,y+h]
def overlaps(a,b,gap=8.64):return min(a[2]+gap,b[2]+gap)-max(a[0],b[0])>1e-6 and min(a[3]+gap,b[3]+gap)-max(a[1],b[1])>1e-6
def fit_origin(c,t,sz):
 x,y=c['origin_um'];nw,nh=sz;tw,th=t['outline_um'];obs=[box(z) for z in t['hard_cores'] if z is not c]
 # nearest legal lattice placement, bounded by the existing registered reach.
 for dist in range(48):
  ds=[(dx,sgn*(dist-abs(dx))) for dx in range(-dist,dist+1) for sgn in ([1,-1] if abs(dx)!=dist else [1])]
  for dx,dy in ds:
   xx=round(x+8.64*dx,4);yy=round(y+8.64*dy,4);b=[xx,yy,xx+nw,yy+nh]
   if xx>=0 and yy>=0 and b[2]<=tw+1e-6 and b[3]<=th+1e-6 and not any(overlaps(b,z) for z in obs):return[xx,yy]
 # If the local slot is boxed in, search the exact free rectangles at obstacle
 # edges; no sibling body is moved and any added reach is explicitly reported.
 snap=lambda q:round(math.ceil(q/8.64)*8.64,4)
 xs={x,8.64,max(0,snap(tw-nw-8.64))};ys={y,8.64,max(0,snap(th-nh-8.64))}
 for z in obs:
  xs.update([snap(z[2]+8.64),snap(z[0]-nw-8.64)]);ys.update([snap(z[3]+8.64),snap(z[1]-nh-8.64)])
 for xx,yy in sorted(((xx,yy) for xx in xs for yy in ys),key=lambda q:abs(q[0]-x)+abs(q[1]-y)):
  b=[xx,yy,xx+nw,yy+nh]
  if xx>=0 and yy>=0 and b[2]<=tw+1e-6 and b[3]<=th+1e-6 and not any(overlaps(b,z) for z in obs):return[xx,yy]
 return None
newpins={};report=[]
for m,ss in variants.items():
 if 'cxport' in m and '--skip-cxport' in sys.argv[4:]:continue
 sz=ss[variant-1];files={};rows=[]
 for tn,t in d['partition_types'].items():
  for c in t.get('hard_cores',[]):
   if c['module']!=m:continue
   old=copy.deepcopy(c);o=fit_origin(c,t,sz)
   if o is None:rows.append({'type':tn,'inst':c['inst'],'status':'NO_ROOM'});continue
   W,H=old['outline_um'];NW,NH=sz;f=c['pins_file'];nf=f[:-5]+f'__codex_v{variant}.json'
   if f not in files:
    ps=json.load(open(base/f))
    for p in ps:
     # Boundary pins retain ordering and relative span; snap the layer-normal
     # coordinate to the same PDK track grid, preserving every name/width.
     face=min([(p['x'],'W'),(W-p['x'],'E'),(p['y'],'S'),(H-p['y'],'N')])[1]
     if min(p['x'],W-p['x'],p['y'],H-p['y'])<.5:
      if face in ['W','E']:
       p['x']=p['x'] if face=='W' else round(p['x']+NW-W,4);p['y']=p['y']/H*NH
      else:
       p['x']=p['x']/W*NW;p['y']=p['y'] if face=='S' else round(p['y']+NH-H,4)
      axis='x' if p['layer'] in ['M3','M5','M7','M9'] else 'y';off,pitch=(.024,.048) if p['layer'] in ['M4','M5'] else ((.032,.064) if p['layer'] in ['M6','M7'] else (.009,.036));p[axis]=round(off+round((p[axis]-off)/pitch)*pitch,4)
    # Refuse accidental name, track or position collisions after shrinking.
    keys=[(p['layer'],round(p['x'],4),round(p['y'],4)) for p in ps]
    assert len(keys)==len(set(keys)),('pin collision',m)
    newpins[nf]=ps;files[f]=nf
   c.update(origin_um=o,outline_um=sz,pins_file=files[f]);c['note']=c.get('note','')+' | CODEX measured outline fix; die rebuild and station resite required'
   e=ce.get(tn,{}).get(c['inst'])
   if e:
    xy=[round(e['xy_um'][0]+(NW-W)/2,4),round(e['xy_um'][1]+(NH-H)/2,4)]
    if 'sfustore' in m:xy=[round(NW/2+.024,4),194.4 if variant==1 else 129.6]
    xy[0]=round(.024+round((xy[0]-.024)/.048)*.048,4);e['xy_um']=xy;e['island_um']=[round(xy[0]-.024-4.32,4),round(xy[1]-4.32,4),round(xy[0]-.024+4.32,4),round(xy[1]+4.32,4)]
    e['source']='CODEX outline-root geometry; preserve 250/202.5ps targets, fresh core and die clocks required'
   rows.append({'type':tn,'inst':c['inst'],'status':'PREP','old_origin':old['origin_um'],'new_origin':o,'old_size':old['outline_um'],'new_size':sz})
 if any(r['status']=='NO_ROOM' for r in rows):raise RuntimeError(('NO_ROOM',m,rows))
 cm['cores'][m]['outline_um']=sz
 if 'sfustore' in m:
  nc=3 if variant==1 else 4
  for k,q in enumerate(cm['cores'][m]['macros']):
   x=15.12+(k%nc)*(94.824+21.6);y=15.12+(k//nc)*(41.064+21.6)
   q['rect_um']=[round(x,4),round(y,4),round(x+94.824,4),round(y+41.064,4)];q['orient']='R0'
  cm['cores'][m]['basis']='explicit 21.6um clock/logic corridors with 4.32um halo; root in horizontal street'
 report.append({'module':m,'variant':variant,'instances':rows,'added_cycles':0})
for f in base.rglob('*'):
 r=f.relative_to(base);p=out/r
 if p.exists() or r.name in ['die_plan.json','core_macros.json','clock_entries.json']:continue
 if f.is_dir():p.mkdir(parents=True,exist_ok=True)
 elif f.is_file():
  p.parent.mkdir(parents=True,exist_ok=True)
  try:os.link(f,p)
  except OSError:shutil.copy2(f,p)
for f,x in newpins.items():p=out/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=1))
d['die']['label']=f'CODEX outline fix variant{variant} PREP | '+d['die']['label']
for f,x in [('die_plan.json',d),('clock_entries.json',ce),('core_macros.json',cm)]: (out/f).write_text(json.dumps(x,indent=1))
(out/'outline_delta_report.json').write_text(json.dumps({'schema':'opentallas.hbm.outline_delta.v1','variant':variant,'fixes':report,'die_rebuild_required':True,'station_resite_required':True,'release_claim':False},indent=1))
print('variant',variant,[(x['module'],len(x['instances'])) for x in report])
