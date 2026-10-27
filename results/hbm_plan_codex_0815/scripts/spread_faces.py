"""Spread unchanged pin-face/order assignments to the existing <=60 pins / closed10um rule. No face reassignment guesses."""
import json,sys,pathlib,collections,math,hashlib
pd=pathlib.Path(sys.argv[1]);census=json.load(open(sys.argv[2]));allow={r.get('pins_file') for r in census['records'] if r['kind']=='core' and r['verdict']=='FAIL'};d=json.loads((pd/'die_plan.json').read_text());by={};rep={'changed':[],'insufficient_face_capacity':[],'scope':'core tables only; no RTL/cycle changes, final windows independently recounted'}
for tn,t in d['partition_types'].items():
 for hc in t.get('hard_cores',[]):
  if hc.get('pins_file'):by.setdefault(hc['pins_file'],hc)
def pname(p):return p.get('name') or (str(p['bus'])+'['+str(p.get('bit',0))+']')
for pf,hc in by.items():
 if pf not in allow:continue
 obj=json.loads((pd/pf).read_text());pins=obj.get('pins',obj) if isinstance(obj,dict) else obj;w,h=hc['outline_um'];faces=collections.defaultdict(list)
 for p in pins:
  if pname(p).upper().startswith(('VDD','VSS')):continue
  ds=[p['x'],w-p['x'],p['y'],h-p['y']]
  if min(ds)<=2:faces['WESN'[ds.index(min(ds))]].append(p)
 new=[];blocked=[]
 for f,ps in faces.items():
  L=h if f in 'WE' else w;axis='y' if f in 'WE' else 'x';span=L-17.28
  # Current face must have enough perimeter under the existing density rule. No relocation to another face here.
  if len(ps)>max(0,math.floor(span*5.9)):
   blocked.append(dict(face=f,pins=len(ps),usable_um=round(span,6),minimum_length_at6_um=round(len(ps)/6+17.28,6)));continue
  ordered=sorted(ps,key=lambda p:(p[axis],pname(p)));lo=math.ceil((8.64-.024)/.048);hi=math.floor((L-8.64-.024)/.048)
  tracks=[round(lo+(hi-lo)*(i+.5)/len(ps)) for i in range(len(ps))]
  assert len(set(tracks))==len(ps)
  coords=[.024+.048*x for x in tracks]
  # Explicit closed-window count, including pins across every layer on this face.
  j=0;peak=0
  for i,x in enumerate(coords):
   while j<len(coords) and coords[j]-x<=10+1e-9:j+=1
   peak=max(peak,j-i)
  if peak>60:blocked.append(dict(face=f,pins=len(ps),reason='closed-window capacity still exceeds60',peak=peak));continue
  for p,k in zip(ordered,tracks):
   old=p[axis];p[axis]=round(.024+.048*k,6)
   if p[axis]!=old:new.append(dict(pin=pname(p),face=f,old=old,new=p[axis]))
 if new:
  (pd/pf).write_text(json.dumps(obj,indent=1)+'\n');rep['changed'].append(dict(table=pf,pins_moved=len(new),changes=new))
 if blocked:rep['insufficient_face_capacity'].append(dict(table=pf,module=hc['module'],outline=hc['outline_um'],faces=blocked))
(pd/'spread_faces_report.json').write_text(json.dumps(rep,indent=1)+'\n');print('spread views',len(rep['changed']),'capacity-blocked views',len(rep['insufficient_face_capacity']))
