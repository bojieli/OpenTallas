#!/usr/bin/env python3
"""Expand A2F midcapd into actual field4 children and route every original bitnet plus replicated local control.
No inherited field16 pin locations: field4 endpoints use assigned pin tables. All128SRAM/53sources/3slots retained.
The W0 proposed re-outline/payload pin plan and other old inventory geometry retain a2f_route_plan scope limits.
"""
import argparse,copy,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import a2f_route_plan as F
R=F.R;ROOT=HERE.parents[1];CH=R.CH
FIELD='s81_a2f_field4';CTL='s81_a2f_control4_resetlocal'
def table(file):
 s=json.loads((ROOT/file).read_text());xy={}
 for p in s['pins']:
  n=p['port'];base=n.split('[')[0];b=int(n.split('[')[1][:-1]) if '[' in n else 0;xy[(base,b)]=(p['x_um'],p['y_um'])
 return lambda p,b:xy[(p,b)]
def expand(P,nets):
 old=P.leaves;new=[];remap={};groups={};pos={};d=table('physical/s81_vm_a2f_split4_2118/s81_a2f_field4.pins.json')
 for i,l in enumerate(old):
  if l['master']!='s81_a2f_field16':
   n=dict(l);remap[i]=len(new);new.append(n);pos[len(new)-1]=P.pos[i]
   if n['master']=='s81_a2f_control4':n['master']=CTL;n['geo']=None;n['pins_fn']=table('physical/s81_vm_a2f_control_resetlocal_2118/s81_a2f_control4_resetlocal.pins.json')
   continue
  ids=[];x,y,fx,fy=P.pos[i]
  for k in range(4):
   j=len(new);ids.append(j);lx=(k%2)*(86.4+CH);ly=(k//2)*(129.6+CH)
   if fx:lx=l['w']-lx-86.4
   if fy:ly=l['h']-ly-129.6
   new.append(dict(name=l['name']+f'.bitslice[{k}].u_leaf',master=FIELD,w=86.4,h=129.6,geo=None,
    ports=dict(i_data=212,i_sel=672,i_drain_v=32,i_drain_slot=64,o_v=32,o_data=128,fault=4),pins_fn=d))
   pos[j]=(x+lx,y+ly,fx,fy)
  groups[i]=ids
 def ep(e):
  i,p,b=e
  if i<0:return [e]
  if i not in groups:return [(remap[i],p,b)]
  ids=groups[i]
  if p in ('i_data','o_data'):
   k=(b%16)//4;return [(ids[k],p,(b//16)*4+b%4)]
  if p in ('o_v','fault'):return [(ids[0],p,b)]
  return [(j,p,b) for j in ids]
 nn=[]
 for net in nets:
  seen=set();n=[]
  for e in net:
   for q in ep(e):
    if q not in seen:seen.add(q);n.append(q)
  nn.append(n)
 Q=R.Plan(new);Q.pos=pos
 return Q,nn

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--passes',type=int,default=10);ap.add_argument('--out',default=str(ROOT/'results/arch/s81_vm_split4_2118/route_plan.json'));a=ap.parse_args()
 F.install_pin_models();baseface=R.port_face;cdc=('aSW','t_wfc','f_wfc','sel','col','qSW','t_gather');R.port_face=lambda p:'E' if p.startswith(cdc) else baseface(p)
 leaves,nets=R.load();ol=dict(F.OUTLINES);ol.update(s81_a2f_field16=(194.4,280.8),s81_a2f_meta26=(259.2,162.0),s81_a2f_control4=(194.4,129.6))
 leaves,nets=F.transform(leaves,nets,ol);vo=copy.deepcopy(F.VARIANTS['midcapd']);P,W,H,struct=F.build_mid(leaves,nets,3369.6,vo)
 P,nets=expand(P,nets)
 oldpm=R.pin_models
 def pm(leaves):
  models=oldpm([l for l in leaves if l['master'] not in (FIELD,CTL)])
  models[FIELD]={};models[CTL]={};return models
 R.pin_models=pm
 bad,outside=P.check(W,H);pg=R.pg_plan(P,W,H)
 ev=R.routed_report(P,nets,W,H,100.0,pg=pg,passes=a.passes)
 res=dict(schema='opentallas.s81.vm-a2f-split4-route-plan.v1',status='ACTUAL_ASSIGNED_FIELD4_PINS_SCREEN_NOT_GRT',rectangle_um=[W,H],area_mm2=W*H/1e6,leaves=len(P.leaves),legality=dict(spacing_violations=bad,outside=outside,channel_um=CH),cuts=ev,pg=pg,structure=struct,source_tools={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),HERE/'a2f_route_plan.py',HERE/'a2_route_plan.py']},not_claimed=['Native die clock/reset delivery','GRT/DRT proof','Unmeasured meta26 closure','Actual W0 proposed re-outline closure','Programme relay price'],placement={P.leaves[i]['name']:[P.leaves[i]['master']]+list(P.rect(i))+list(P.pos[i][2:]) for i in sorted(P.pos)})
 out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(res,indent=1,default=float)+'\n')
 import a2_floorplan as FP
 FP.svg(P,W,H,str(out.with_suffix('.svg')))
 print(json.dumps({k:res[k] for k in ['rectangle_um','area_mm2','leaves','legality']}),flush=True);print(json.dumps({k:v for k,v in ev.items() if k not in ('hot','over_reach_pairs')}),flush=True)
if __name__=='__main__':main()
