"""Read-only audit of Claude cd32f2a18 control centres expanded to legal 4.32um regions."""
import json,pathlib,sys,itertools,hashlib
root=pathlib.Path('results/arch/qw_cb16_legal_bays_1020/grid43');name=sys.argv[1];d=json.loads((root/(name+'_control_inputs.json')).read_text());sp=root/(name+'_control_solution.json');s=json.loads(sp.read_text());assert set(s['pos'])==set(d['scalar']);rects={n:[x-2.16,y-2.16,4.32,4.32] for n,(x,y) in s['pos'].items()};errs=[];W,H=d['outline']
def corners(r):x,y,w,h=r;return [(x,y),(x+w,y),(x,y+h),(x+w,y+h)]
def overlap(a,b):x,y,w,h=a;xx,yy,ww,hh=b;return x<xx+ww-1e-6 and xx<x+w-1e-6 and y<yy+hh-1e-6 and yy<y+h-1e-6
for n,r in rects.items():
 x,y,w,h=r
 if not(0<=x<=W-w and 0<=y<=H-h):errs.append(('outline',n))
 for q,b in {**d['hard'],**d['bays']}.items():
  if overlap(r,b):errs.append(('obstacle',n,q))
for (n,a),(q,b) in itertools.combinations(rects.items(),2):
 if overlap(a,b):errs.append(('overlap',n,q))
def pts(e):
 if 'node' in e:return corners(rects[e['node']])
 if 'box' in e:return corners(e['box'])
 return [e['point']]
rows=[]
for e in d['edges']:
 reach=max(abs(x-xx)+abs(y-yy) for x,y in pts(e['src']) for xx,yy in pts(e['dst']));rows.append((reach,e))
 if reach>405+1e-6:errs.append(('reach',reach,e))
report={'status':'FAIL' if errs else 'PASS','scalar_regions':len(rects),'dynamic_edges':len(rows),'max_all_corner_um':max(r[0] for r in rows),'static_straps':len(d['static_straps']),'unknown':len(d['unknown']),'errors':errs,'solution_sha256':hashlib.sha256(sp.read_bytes()).hexdigest(),'scope':'candidate4.32um legal square regions around committed AC centres; no kit mutation; actual legal row capacity and source native/clock remain owed'}
(root/(name+'_legal_box_audit.json')).write_text(json.dumps(report,indent=2)+'\n');(root/(name+'_legal_box_candidate.json')).write_text(json.dumps(rects)+'\n');print('LEGAL_BOX_AUDIT',name,report['status'],report['max_all_corner_um']);assert not errs
