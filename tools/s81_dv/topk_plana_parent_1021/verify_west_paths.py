#!/usr/bin/env python3
"""Literal public pin route-length feasibility; not cell placement or routing."""
import re,json,math,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[3]
O=R/'results/arch/s81_topk_plana_parent_1021/west_paths.json'
def lef(path):
 s=(R/path).read_text(); d={}
 for m in re.finditer(r'  PIN ([^\n]+)\n(.*?)\n  END \1\n',s,re.S):
  rect=re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',m[2])
  if rect:
   a,b,c,e=map(float,rect.groups()); d[m[1]]=((a+c)/2,(b+e)/2)
 return d,hashlib.sha256(s.encode()).hexdigest()
q,qsha=lef('physical/ref_tile/s81dvbk_sq_hq3/views/dsdv_bksel_q/dsdv_bksel_q.lef')
g,gsha=lef('physical/ref_tile/s81dvbk_g2/views/dsdv_bk_g/dsdv_bk_g.lef')
c,csha=lef('physical/ref_tile/s81dvbk_selc2/views/dsdv_bksel_c/dsdv_bksel_c.lef')
md=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
yq=[43.2,864,1771.2,2548.8]; west=205.2; bottom=1533.6;top=1749.6
bodies=[(216,y,864,y+648)for y in yq]+[(216,1555.2,604.8,1728),(648,1555.2,864,1728)]
def inside(p):return any(a+1e-6<p[0]<c-1e-6 and b+1e-6<p[1]<d-1e-6 for a,b,c,d in bodies)
def point_at(path,t):
 for a,b in zip(path,path[1:]):
  z=md(a,b)
  if t<=z+1e-9:
   if z==0:return a
   return (a[0]+(b[0]-a[0])*t/z,a[1]+(b[1]-a[1])*t/z)
  t-=z
 return path[-1]
# nearest 54nm placement site/270nm row, reference-only cell centers
snap=lambda p:(round(p[0]/.054)*.054,round(p[1]/.270)*.270)
rows=[];points=[]
def record(quarter,kind,bit,path,pin1,pin2,proxy=False):
 length=sum(md(a,b)for a,b in zip(path,path[1:])); stages=[snap(point_at(path,length*k/7))for k in range(8)]
 assert all(not inside(p) for p in stages),(quarter,kind,bit,stages)
 distances=[md(a,b)for a,b in zip(stages,stages[1:])]
 # Path route length, not straight through macro obstacles. Snapping perturbation bound.
 routed_bound=length/7+max(md(a,b)for a,b in zip(stages,[point_at(path,length*k/7)for k in range(8)]))*2
 rows.append(dict(q=quarter,kind=kind,bit=bit,route_um=length,max_hop_bound_um=routed_bound,max_manhattan_um=max(distances),local_pin_um=max(md(pin1,path[0]),md(pin2,path[-1])),control_proxy=proxy))
 points.extend((quarter,kind,k,*p)for k,p in enumerate(stages))
for j in range(4):
 central=bottom if j<2 else top
 rail=yq[j]+658.8
 def qp(n):x,y=q[n];return(x+216,y+yq[j])
 for b in range(515):
  gx,gy=g[f'ln{j}[{b}]'];a=(gx+648,gy+1555.2);z=qp(f'lane[{b}]')
  wb=(637.2 if gx<108 else 874.8,a[1]); rb=(z[0],rail)
  # Near quarter1 direct N/S facing path; banks may be padded locally but capacity unqualified.
  if j==1:path=[wb,(wb[0],central),(rb[0],central),rb]
  else:path=[wb,(wb[0],central),(west,central),(west,rail),rb]
  record(j,'lane',b,path,a,z)
 for kind,w,qn,cn in [('status',865,'t_s','f_s'),('command',66,'f_c','t_c'),('credit',1,'f_cr','t_cr'),('selected',354,'t_o','f_o')]:
  side='s'if j<2 else'n'; offset=(j%2)*w
  for b in range(w):
   z=qp(qn if qn=='f_cr'else f'{qn}[{b}]')
   cp=c[f'{cn}_{side}[{offset+b}]'];a=(cp[0]+216,cp[1]+1555.2)
   wb=(a[0],central)
   rb=(west,z[1])if kind=='selected'else(z[0],rail)
   if j==1 and kind!='selected':path=[wb,(rb[0],central),rb]
   else:path=[wb,(west,central),(west,rb[1]),rb]
   record(j,kind,b,path,a,z,True)
# Local VD: literal c2 proxy-to-g pins and one relay at the center of 43.2 gap.
vd=[]
for b in range(514):
 a=(c[f'vd[{b}]'][0]+216,c[f'vd[{b}]'][1]+1555.2);z=(g[f'vd[{b}]'][0]+648,g[f'vd[{b}]'][1]+1555.2)
 relay=(626.4,1641.6);vd += [md(a,relay),md(relay,z)]
# Raw preferred direction tracks per um from published ASAP7 tech. No routing grant inferred.
hraw=7/.270+1/.048+1/.064;vraw=1/.036+1/.048+1/.064
n_data=515+66+1+865;n_valid=math.ceil(257/12)+math.ceil(258/12)+math.ceil(67/12)+math.ceil(288/12)*2+math.ceil(289/12)
result=dict(status='PER_BIT_PATH_FEASIBILITY_ONLY_BODY_FENCE_CTS_ROUTE_OPEN',quarter_lef_sha256=qsha,glue_lef_sha256=gsha,control_PROXY_c2_lef_sha256=csha,checks=len(rows),max_hop_bound_um=max(x['max_hop_bound_um']for x in rows),max_local_pin_um=max(x['local_pin_um']for x in rows),worst=max(rows,key=lambda x:x['max_hop_bound_um']),per_quarter={str(j):max(x['max_hop_bound_um']for x in rows if x['q']==j)for j in range(4)},local_VD_proxy_max_um=max(vd),capacity=dict(N_bundle_data=n_data,chunk12_valid=n_valid,D2_two_banks_wires=2*(n_data+n_valid),horizontal_raw_tracks_per_um=hraw,top_band_um=86.4,top_raw_tracks=86.4*hraw,top_min_raw_occupancy=2*(n_data+n_valid)/(86.4*hraw),old43p2_min_raw_occupancy=2*(n_data+n_valid)/(43.2*hraw),west_vertical_raw_tracks=216*vraw),debts=['Control endpoint coordinates are OLD c2 proxy only; new c_pa pins not qualified or aliased.','Point anchors do not place actual landing cells, pin access, valid/reset/clock copies or region fences.','Seven equal-length bit routes do not prove simultaneous disjoint routing; per-root body and cut capacity required.','Direct quarter1 paths require local placement of repeated padding banks; no west-spine spill or density proof.','Rung source-to-spine per-bit paths and body allocation remain open.','No physical fit or same-throughput claim.'])
result['capacity']['top_core_available_um']=84.24
result['capacity']['top_core_raw_tracks']=84.24*hraw
result['capacity']['top_core_min_raw_occupancy']=2*(n_data+n_valid)/(84.24*hraw)
O.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
