#!/usr/bin/env python3
"""Estimate L2 lot compaction on current mirrored gunit; no plan/RTL mutation or route authority."""
import collections,copy,json,re,sys
from pathlib import Path
r=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
base=r/'physical/die_plan/s81';plan=json.load(open(base/'die_plan.json'))
type_=plan['partition_types']['gunit__t1'];cores={c['inst'].split('.')[-1]:c for c in type_['hard_cores']}
rtl=(r/'rtl/dsrom_sys/s81_dv/unit/dsdv_gunit.sv').read_text();rtl=re.sub(r'//[^\n]*','',rtl)
conn=collections.defaultdict(list)
for inst in cores:
 m=re.search(r'\b'+inst+r'\s*\((.*?)\);',rtl,re.S)
 if not m:continue
 for p,n in re.findall(r'\.(\w+)\s*\(\s*([A-Za-z_]\w*)\s*\)',m[1]):
  if n not in ('clk','rst_n'):conn[n].append((inst,p))
pins={i:json.load(open(base/c['pins_file']))['pins'] for i,c in cores.items()}
def point(c,p):
 x,y=p['x'],p['y'];w,h=c['outline_um'];o=c.get('orient','R0')
 if o in ('MY','R180'):x=w-x
 if o in ('MX','R180'):y=h-y
 assert o in ('R0','MX','MY','R180'),o
 return c['origin_um'][0]+x,c['origin_um'][1]+y
def census(cs,ps):
 pp={}
 for i,c in cs.items():
  for p in ps[i]:
   m=re.fullmatch(r'(\w+)(?:\[(\d+)\])?',p['name']);pp[i,m[1],m[2]]=point(c,p)
 results={}
 for net,e in conn.items():
  if len(e)!=2:continue
  (ia,pa),(ib,pb)=e;ka={k[2]:v for k,v in pp.items() if k[:2]==(ia,pa)};kb={k[2]:v for k,v in pp.items() if k[:2]==(ib,pb)}
  if ia!='u_l2' and ib!='u_l2':continue
  vals=[abs(a[0]-kb[b][0])+abs(a[1]-kb[b][1]) for b,a in ka.items() if b in kb]
  if vals:results[net]=dict(ports=e,bits=len(vals),maximum_um=round(max(vals),3),over405=sum(v>405 for v in vals))
 return results
old=cores['u_l2'];new=copy.deepcopy(old);new['outline_um']=[259.2,43.2];new['origin_um'][0]+=86.4
np=copy.deepcopy(pins['u_l2']);faces=collections.defaultdict(list)
for p in np:
 x,y=p['x'],p['y'];f=min(dict(W=x,E=345.6-x,S=y,N=43.2-y),key=dict(W=x,E=345.6-x,S=y,N=43.2-y).get);faces[f].append(p)
for face,rows in faces.items():
 rows.sort(key=lambda p:(p['x'] if face in ('N','S') else p['y'],p['name']))
 for j,p in enumerate(rows):
  if face in ('N','S'):
   x=2.16+(259.2-4.32)*j/max(1,len(rows)-1)
   p['x']=round(.012+round((x-.012)/.048)*.048,6)
  elif face=='E':p['x']=round(259.2-(345.6-p['x']),6)
cs=copy.deepcopy(cores);ps=copy.deepcopy(pins);cs['u_l2']=new;ps['u_l2']=np
report=dict(scope='ESTIMATE ONLY: exact core orientations respected; direct-net endpoints, no relay/cycle or G0 claim',old_outline=old['outline_um'],new_outline=new['outline_um'],old_origin=old['origin_um'],new_origin=new['origin_um'],old_fill=0.1164,new_fill=0.1164*345.6/259.2,face_density_per_um={f:len(v)/(259.2 if f in ('N','S') else 43.2) for f,v in faces.items()},baseline=census(cores,pins),candidate=census(cs,ps))
station=next(x for x in type_['internal_stations'] if x.get('conn')=='bus:unit_i0')
reg=station['regs_um'][0]
legs=[abs(new['origin_um'][0]+p['x']-reg[0])+abs(new['origin_um'][1]+p['y']-reg[1]) for p in np if re.match(r'^cw_(?:d|a|v)(?:\[|$)',p['name'])]
report['unit_i0_existing_station_capture']=dict(station_um=reg,bits=len(legs),maximum_um=round(max(legs),3),over405=sum(v>405 for v in legs))
json.dump(report,open(out/'l2_estimate.json','w'),indent=2);json.dump(dict(core=new,pins=np),open(out/'l2_candidate.json','w'),indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('baseline','candidate')},indent=2))
for net,b in report['baseline'].items():
 n=report['candidate'][net];print(net,b['ports'],b['maximum_um'],b['over405'],'->',n['maximum_um'],n['over405'])
