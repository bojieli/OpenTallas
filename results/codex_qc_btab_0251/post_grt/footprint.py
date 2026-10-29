"""Post-GRT census of the exact planned clock/FT footprint, with no design mutation."""
import json,sys
from pathlib import Path
plan=json.load(open(sys.argv[1])); block=json.load(open(sys.argv[3])); cells={};macros=[]
for line in Path(sys.argv[2]).read_text().splitlines():
 s=line.split('\t')
 if s[0]=='C':
  x=dict(kind=s[2],master=s[3],box=list(map(float,s[4:8])),name=s[8]);cells[x['name']]=x
  if x['kind']=='M':macros.append(x)
def hit(a,b):return a[0]<b[2]-1e-6 and b[0]<a[2]-1e-6 and a[1]<b[3]-1e-6 and b[1]<a[3]-1e-6
missing=[];moved=[];body=[];halo=[];hard=[]
for c in plan['cells']:
 n=c['name'];a=cells.get(n)
 if a is None:missing.append(n);continue
 if a['master']!=c['master'] or any(abs(a['box'][j]-c['origin_um'][j])>0.0002 for j in [0,1]):moved.append(n)
 for m in macros:
  b=m['box'];h=[b[0]-4.32,b[1]-4.32,b[2]+4.32,b[3]+4.32]
  if hit(a['box'],b):body.append([n,m['name']])
  if hit(a['box'],h):halo.append([n,m['name']])
 for b in block:
  if hit(a['box'],[z/1000 for z in b['rect']]):hard.append([n,b['name']])
x=dict(planned_cells=len(plan['cells']),actual_macros=len(macros),missing=missing,moved_or_master_changed=moved,body_overlap=body,halo_overlap=halo,hard_blockage_overlap=hard)
x['verdict']='PASS' if not any([missing,moved,body,halo,hard]) else 'FAIL'
print(json.dumps(x,indent=1))
sys.exit(0 if x['verdict']=='PASS' else 1)
