import json,sys
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
from exact_cones import endpoints,physical_port_map
P=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/home/ubuntu/coord/tmp/codex-hist-anchor-2100');C=json.load(open(P/'repack_B_complete.json'));D=G.Design(P/'geom.tsv');pm=physical_port_map(C);fixedFF={x['cid']for x in C['fixed']if x['cid']in D.cells and D.kind(x['cid'])=='S'}
fp=[];mm=[]
for cid in fixedFF:
 ins,mi=endpoints(D,cid,False);out,mo=endpoints(D,cid,True);x,y=G.ctr(D.cells[cid])
 for k in mi|mo:
  for X,Y,n in pm[k]:
   d=abs(x-X)+abs(y-Y)
   if d>405+1e-6:fp.append(dict(ff=D.cells[cid][6],macro_port=n,distance_um=round(d,4)))
# Follow each exact macro output net through only combinational cells, stopping at FFs/hard macros.
for (src,ni,io),start in pm.items():
 if io!='OUTPUT':continue
 todo=[ni];seen=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n);sig,dr,ss=D.nets[n]
  if sig in('CLOCK','POWER','GROUND'):continue
  for r in ss:
   if r[0]!='i'or r[2]:continue
   kind=D.kind(r[1])
   if kind=='M':
    for x,y,ln in start:
     for X,Y,rn in pm[(r[1],n,'INPUT')]:
      d=abs(x-X)+abs(y-Y)
      if d>405+1e-6:mm.append(dict(launch=ln,capture=rn,distance_um=round(d,4)))
   elif kind in('L','B','K'):todo.extend(D.drives.get(r[1],[]))
a=dict(fixed_face_macro_bad=len(fp),direct_macro_macro_bad=len(mm),face_macro=fp,macro_macro=mm)
(P/'repack_B_direct_fixed.json').write_text(json.dumps(a,indent=1)+'\n');print(json.dumps({k:v for k,v in a.items()if isinstance(v,int)}));print(mm[:3],fp[:3])
