#!/usr/bin/env python3
"""Check exact native term → VIA78 → M8 stripe → VIA89 → M9 in actual ODB."""
import argparse,collections,json
import odb

def inside(a,b):return b[0]<=a[0] and b[1]<=a[1] and a[2]<=b[2] and a[3]<=b[3]
def rect(i,s):
 sx,sy={'R0':(1,1),'MX':(1,-1),'MY':(-1,1),'R180':(-1,-1)}[str(i.getOrient())];ox,oy=i.getOrigin();xx=sorted([ox+sx*s.xMin(),ox+sx*s.xMax()]);yy=sorted([oy+sy*s.yMin(),oy+sy*s.yMax()]);return[xx[0],yy[0],xx[1],yy[1]]
p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--plan',required=True);p.add_argument('--out',required=True);a=p.parse_args();plan=json.load(open(a.plan));assert not plan['failed'];d=odb.dbDatabase.create();odb.read_db(d,a.odb);b=d.getChip().getBlock();wires=collections.defaultdict(list);vias=collections.defaultdict(set)
for n in ['VDD','VSS']:
 net=b.findNet(n);assert net is not None
 for sw in net.getSWires():
  for sh in sw.getWires():
   if sh.isVia():vias[n,sh.getTechVia().getName()].add(tuple(sh.getViaXY()))
   else:wires[n,sh.getTechLayer().getName()].append([sh.xMin(),sh.yMin(),sh.xMax(),sh.yMax()])
checked=[];failures=[]
for c in plan['contacts']:
 n=c['net'];i=b.findInst(c['inst']);it=i.findITerm(c['pin']);x,y=c['xy_dbu'];errors=[]
 if not it.getNet() or it.getNet().getName()!=n:errors.append('actual_iterm_unbound_or_wrong_net')
 pg=[]
 for mp in it.getMTerm().getMPins():
  for sh in mp.getGeometry():
   if sh.getTechLayer() and sh.getTechLayer().getName()=='M7':pg.append(rect(i,sh))
 if not any(inside(c['metal_dbu']['M7'],r) for r in pg):errors.append('actual_native_pin_not_enclosing_contact')
 if (x,y) not in vias[n,'VIA78']:errors.append('actual_via78_missing')
 hh=[r for r in wires[n,'M8'] if inside(c['metal_dbu']['M8'],r)]
 connected=False
 for h in hh:
  for vx,vy in vias[n,'VIA89']:
   r=[vx-20,vy-20,vx+20,vy+20]
   if inside(r,h) and any(inside(r,v) for v in wires[n,'M9']):connected=True;break
  if connected:break
 if not connected:errors.append('no_actual_M8_VIA89_M9_path')
 if errors:failures.append(dict(inst=c['inst'],pin=c['pin'],errors=errors))
 else:checked.append(dict(inst=c['inst'],pin=c['pin'],net=n,via78=[x,y]))
result=dict(verdict='PASS_CONNECTIVITY_COUPON' if not failures else 'FAIL',actual_terms=len(checked),failed=len(failures),actual_via78=sum(len(q) for (n,v),q in vias.items() if v=='VIA78'),actual_via89=sum(len(q) for (n,v),q in vias.items() if v=='VIA89'),actual_grid_rectangles=sum(len(q) for q in wires.values()),checked=checked,failures=failures,scope='One term access per macro supply; no IR/diePG/per-fragment closure')
json.dump(result,open(a.out,'w'),indent=2);print(json.dumps({k:v for k,v in result.items() if k not in ['checked','failures']},indent=2));raise SystemExit(bool(failures))
