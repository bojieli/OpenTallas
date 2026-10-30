"""Keep exact low-y PG prefix geometry for residual diagnosis while full runs progress."""
import json,sys,collections,shutil
from pathlib import Path
r=Path(sys.argv[1]);o=Path(sys.argv[2]);o.mkdir(parents=True,exist_ok=True)
t=json.load(open(r/'readback/power_terms.json'));rows=collections.defaultdict(list)
for a in t['terms']:
 l,x0,y0,x1,y1=a['shapes_dbu'][0];rows[a['pin'],y0,y1].append((x0,x1))
groups=[]
for (n,y0,y1),rr in rows.items():
 rr.sort();cur=None
 for x0,x1 in rr:
  if cur is not None and x0<=cur[1]:cur[1]=max(cur[1],x1)
  else:
   if cur is not None:groups.append((n,*cur,y0,y1))
   cur=[x0,x1]
 if cur is not None:groups.append((n,*cur,y0,y1))
groups.sort(key=lambda x:(x[3],x[1],x[0]));cut=groups[min(7999,len(groups)-1)][4];pad=50000
term=[a for a in t['terms'] if a['shapes_dbu'][0][2]<=cut];t['terms']=term
json.dump(t,open(o/'power_terms.json','w'),separators=(',',':'))
def hit(rect):return rect[1]<=cut+pad and rect[3]>=0
x=json.load(open(r/'readback/geometry.json'))
for k,n in [('obstructions',2),('signal_shapes',3),('existing_supplies',2)]:x[k]=[a for a in x[k] if hit(a[n:])]
x['cells']=[];json.dump(x,open(o/'geometry.json','w'),separators=(',',':'))
e=json.load(open(r/'readback/endpoints.json'));e['endpoints']={k:v for k,v in e['endpoints'].items() if hit([1000*a for a in v['rect_um']])};json.dump(e,open(o/'endpoints.json','w'),separators=(',',':'))
c=json.load(open(r/'reservation/joint_reserved.json'));c=[a for a in c if hit([1000*v for v in a[2:]])];json.dump(c,open(o/'joint_reserved.json','w'),separators=(',',':'));json.dump([],open(o/'clock_seed.json','w'))
for f in ('pg_rects.json','probe_census.json'):shutil.copy(r/'readback'/f,o/f)
json.dump(dict(prefix_y_max_dbu=cut,context_pad_dbu=pad,contacts=len(term),reserved_shapes=len(c),scope='Exact first~8000 low-y PG groups; diagnostic only, whole-die full runs remain authoritative'),open(o/'context.json','w'),indent=2)
print('PREFIX_CONTEXT',len(term),len(c),cut,flush=True)
