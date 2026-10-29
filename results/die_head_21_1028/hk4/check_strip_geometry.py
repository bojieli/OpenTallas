"""Compare real endpoint pin tables before/after the raw strip event."""
import gzip,json,sys
from pathlib import Path
W=Path(__file__).resolve().parents[3];sys.path.insert(0,str(W/'tools/die_plan'))
import schema as S
D=Path(__file__).parent
old=json.load(gzip.open(D.parent/'hk3/plan_hk3.json.gz','rt'));new=json.load(gzip.open(D/'plan_spine_raw.json.gz','rt'))
A,B=S.Plan(old),S.Plan(new)
def pins(P,end,pr):
 n=end['part'];g=P._type_geom(n,end['bus'])
 if g is None:return None
 face,win,layers,order=g;w,h=P.types[P.parts[n]['type']]['outline_um']
 pp=S.pin_positions(dict(pr,face=face,window_um=win,layers=layers,order=order),P.layers)
 def xy(c):return {'W':[0,c],'E':[w,c],'N':[c,h],'S':[c,0]}[face]
 return [(b,l,tuple(round(v,5) for v in P.to_die(n,xy(c)))) for b,l,c in pp]
changed=0;scalar=0;bad=[]
for pid,pr in A.ports.items():
 after=B.ports[pid]
 for side in ['src','dst']:
  if pr[side]['part']=='DIE':continue
  before=pins(A,pr[side],pr);last=pins(B,after[side],after)
  if before!=last:bad.append([pid,side,len(before or []),len(last or [])])
  if pr[side]!=after[side] or A.rect(pr[side]['part'])!=B.rect(after[side]['part']):changed+=1;scalar+=len(before or [])
# All new rectangles must be disjoint, including the old tile array.
parts=list(B.parts);over=[]
for i,n in enumerate(parts):
 a=B.rect(n)
 for m in parts[i+1:]:
  b=B.rect(m)
  if min(a[2],b[2])-max(a[0],b[0])>1e-5 and min(a[3],b[3])-max(a[1],b[1])>1e-5:over.append([n,m])
r={'external_endpoint_pin_table_mismatches':bad,'changed_external_endpoints':changed,'scalar_pins_checked_on_changed_endpoints':scalar,'partition_overlap_pairs':over,'parts':len(parts)}
print(json.dumps(r,indent=1));assert not bad and not over
(D/'strip_geometry.json').write_text(json.dumps(r,indent=1))
