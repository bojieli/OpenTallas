import sys,json,copy,inspect
from pathlib import Path
import numpy as np
S=Path(sys.argv[1]);out=Path(sys.argv[2]);sys.path[:0]=[str(S/'tools/die_plan'),str(S/'physical/die_plan/s81'),str(S)]
import ft_corridor as F,compact_plan
r=json.loads((S/'physical/die_plan/s81/die_plan.json').read_text());tn='serdes__t12';ty=r['partition_types'][tn]
assert not ty.get('hard_cores'), 'This exact-construction vehicle requires an empty digital corridor'
code=inspect.getsource(F.place).replace('def place(', 'def place_other(')
code=code.replace('for slot in sorted(ty["ft_slots"], key=lambda s: -s["width"]):','for slot in sorted(ty["ft_slots"], key=lambda s: -s["width"]):\n            if slot["name"]=="ft4":continue')
exec(compile(code,'<t12-unchanged-other-slots>','exec'),F.__dict__)
F.place_other(r,[tn],split_bits={tn+'/'+s['name']:128 for s in ty['ft_slots']})
model=F.S.Plan(r);pins={(bn,i):(x,y) for bn,i,_,x,y,_ in F.type_pins(model,tn)}
slot=next(s for s in ty['ft_slots'] if s['name']=='ft4');assert slot['stations']==4
nb=slot['width']+1;a=np.array([pins[('ft4_i',i)] for i in range(nb)]);b=np.array([pins[('ft4_o',i)] for i in range(nb)])
w,h=ty['outline_um'];alloc=F.RowAllocator((4.32,4.32,w-4.32,h-4.32),blocked=[],cell_size=F.CELL,column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
for s in ty['ft_slots']:
 if s['name']=='ft4':continue
 for st in s.get('bit_sites_um',[]):
  for x,y in st:alloc.reserve_rectangle((x,y,x+F.CELL[0],y+F.CELL[1]))
sites=[]
for j in range(1,4):
 q=np.zeros((nb,2))
 for i in range(nb):
  path=F.build_path(slot['in_face'],slot['out_face'],a[i],b[i],w,h)
  _,cum=F._cum(path);target,_=F.point_dir(path,cum[-1]*j/4)
  pp,_=alloc.allocate(target,1,max_radius_um=20.0);q[i]=pp[0]
 sites.append(q)
hops=[float(np.abs(x-y).sum(1).max()) for x,y in zip([a,*sites],[*sites,b])]
assert max(hops)<=405, hops
slot['bit_site_cell_um']=list(F.CELL);slot['bit_sites_um']=[(q-np.array(F.CELL)/2).round(6).tolist() for q in sites];slot['regs_um']=[a.mean(0).round(4).tolist()]+[q.mean(0).round(4).tolist() for q in sites]
out.write_text(compact_plan.dumps(r));Path(str(out)+'.report.json').write_text(json.dumps(dict(type=tn,slot='ft4',stations=4,added_cycles=0,hops_um=hops,method='exact paired L arc quarters plus row legalization',planner_padding_failure='394.9 minus10um algorithm reserve; not a 405um clock/reach waiver'),indent=2));print('T12_DIRECT_PASS',hops,'ADDED_CYCLES0',flush=True)
