import json,re,math,collections
from pathlib import Path
R=Path(__file__).resolve().parents[2];s=json.load(open(R/'physical/ref_tile/qfd_vm_rg6.spec.json'));W,H=s['outline']['w'],s['outline']['h'];boxes=[]
for c in s['children']:
 t=next((R/c['view']).glob('*.lef')).read_text();m=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',t);w,h=map(float,m.groups());x,y=c['at'];boxes.append((x,y,x+w,y+h,c['inst']))
def collision(b):
 x,y,X,Y=b
 return any(x<xx+2.16-1e-6 and X>bx-2.16+1e-6 and y<yy+2.16-1e-6 and Y>by-2.16+1e-6 for bx,by,xx,yy,n in boxes)
def fit(face,count):
 w,h=(129.6,12.96) if face in 'SN' else (17.28,64.8);poss=[]
 for depth in range(0,231,1):
  d=depth*2.16
  if d>220:break
  for k in range(math.floor(((W-w) if face in 'SN' else (H-h))/2.16)+1):
   a=k*2.16;x,y=(a,d) if face=='S' else (a,H-h-d) if face=='N' else (d,a) if face=='W' else (W-w-d,a)
   b=(x,y,x+w,y+h)
   if not collision(b):poss.append((d,x,y,w,h))
 chosen=[]
 for d,x,y,w,h in poss:
  if not collision((x,y,x+w,y+h)):
   chosen.append(dict(face=face,at=[round(x,4),round(y,4)],size=[w,h],minimum_boundary_normal_um=round(d,4)));boxes.append((x,y,x+w,y+h,'face'+face+str(len(chosen))))
   if len(chosen)==count:break
 return chosen
# Uniform full face registration: core RX,core TX,X RX,X TX rounded independently byface.
requests={'S':13,'N':6,'W':18,'E':17};out={f:fit(f,n) for f,n in requests.items()};a=dict(schema='opentallas.vm-face-placement-candidate.v1',claim='Compute-only greedy bbox fit with2.16um macro channels. No pin-wire/PG/CTS/route/epoch proof.',outline_um=[W,H],requested_counts=requests,placed_counts={f:len(v) for f,v in out.items()},placements=out)
(R/'results/arch/qwen_tp8_1012/rg6_face_placement_candidate.json').write_text(json.dumps(a,indent=1)+'\n');print(a['placed_counts']);print({f:max([v['minimum_boundary_normal_um'] for v in vv],default=0) for f,vv in out.items()})
