#!/usr/bin/env python3
"""Pack current hard crossing children around the reviewed sixteen-A0 rpf lattice.
Planning artifact only; no kit, clock reference, route or reach qualification.
"""
import json, math, pathlib, argparse
p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--out',required=True);p.add_argument('--narrow',action='store_true');a=p.parse_args()
s=json.loads(pathlib.Path(a.input).read_text());W,H=2445.12,5227.2;U=4.32
shapes={'qfd_c_stn514':(51.84,51.84),'qfd_c_stn516':(51.84,51.84),'qfd_c_xstn_safe':(90.72,129.6),'qfd_c_xstnw_safe':(90.72,129.6),'qfd_c_ring514':(108,43.2),'qfd_c_ring516':(108,43.2)}
newx=[86.4+604.8*i for i in range(4)];newy=[86.4+1296*i for i in range(4)];oldx=[172.8,950.4,1684.8,2462.4];oldy=[129.6+1339.2*i for i in range(4)]
if a.narrow:
 shapes.update(qfd_c_ring514=(90.72,64.8),qfd_c_ring516=(90.72,64.8),qfd_c_xstn_safe=(43.2,302.4),qfd_c_xstnw_safe=(43.2,302.4))
placed=[];todo=[]
for c in s['children']:
 n=c['inst'];m=c['view'].split('/')[-1]
 if n.startswith('u_t_'):
  col,row=map(int,n[4:].split('_'));placed.append(dict(inst=n,master=m,at=[newx[col],newy[row]],size=[457.92,1157.76],orient=c['orient'],scope='reviewed rpf geometry, A0 gate pending'))
 else:
  col=min(range(4),key=lambda i:abs(c['at'][0]-oldx[i]));row=min(range(4),key=lambda i:abs(c['at'][1]-oldy[i]));target=[c['at'][0]+newx[col]-oldx[col],c['at'][1]+newy[row]-oldy[row]];todo.append(dict(inst=n,master=m,size=list(shapes[m]),orient=c['orient'],target=target))
def clear(x,y,w,h,b):
 bx,by=b['at'];bw,bh=b['size'];return x+w+20<=bx+1e-6 or bx+bw+20<=x+1e-6 or y+h+20<=by+1e-6 or by+bh+20<=y+1e-6
# Crossings cannot fit vertical corridors at 20um clearance; place rings first in row channels.
todo.sort(key=lambda t:(0 if 'ring' in t['master'] else 1 if 'xstn' in t['master'] else 2,t['inst']))
failed=[]
for t in todo:
 w,h=t['size'];tx,ty=t['target'];candidates=[]
 # Every candidate lies on the physical 4.32um origin grid. Enumerate only empty corridor strips.
 for yi in range(1,math.floor((H-h)/U)):
  y=yi*U
  # y inside a tile row: only vertical corridors can hold the child.
  spans=[(4.32,W-w-4.32)]
  for ry in newy:
   if not(y+h+20<=ry or y>=ry+1157.76+20):
    spans=[(4.32,newx[0]-w-20)]+[(newx[i]+457.92+20,newx[i+1]-w-20)for i in range(3)]+[(newx[3]+457.92+20,W-w-4.32)];break
  for lo,hi in spans:
   if hi<lo:continue
   # Nearest grid positions plus boundaries; occupied candidates trigger the next grid point.
   for xi in range(max(1,math.ceil(lo/U)),math.floor(hi/U)+1):
    x=xi*U;cost=abs(x-tx)+abs(y-ty)
    candidates.append((cost,x,y))
 candidates.sort()
 for cost,x,y in candidates:
  if all(clear(x,y,w,h,b)for b in placed):
   placed.append({k:v for k,v in t.items()if k!='target'}|dict(at=[round(x,5),round(y,5)],target=t['target'],displacement_um=round(cost,3)));break
 else:failed.append(t)
 print(t['inst'], 'UNPLACED' if failed and failed[-1]is t else placed[-1]['at'],flush=True)
viol=[]
for i,b in enumerate(placed):
 for c in placed[:i]:
  if not clear(*b['at'],*b['size'],c):viol.append([b['inst'],c['inst']])
O=pathlib.Path(a.out);O.mkdir(parents=True,exist_ok=True)
d=dict(status='PACKING_PASS'if not failed and not viol else'PACKING_FAIL',release_ready=False,outline=[W,H],a0_count=16,hard_child_count=len(placed),clearance_um=20,origin_grid_um=U,unplaced=failed,clearance_violations=viol,placement=placed,scope='geometry packing candidate only; all current hard child sizes retained; no fabricated views or topology',next=['compose actual pin-to-pin connectivity/reach against new A0 rpf pins','compose real clock/reset entry contracts, scalar sites and cycle ages','A0 r3 terminal gates and ROM-LSL band demand','independent GEOM review before any P&R'])
(O/'plan.json').write_text(json.dumps(d,indent=1)+'\n')
print(json.dumps({k:d[k]for k in ['status','hard_child_count','unplaced','clearance_violations']}))
