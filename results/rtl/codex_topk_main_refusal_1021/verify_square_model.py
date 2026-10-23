#!/usr/bin/env python3
"""SOURCE/MODEL only: literal published pins, prospective face bounds, no PPL/view claim."""
import re,json,math,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
spec=json.loads((ROOT/'physical/ref_tile/s81dvbk_selcpn_e/spec.json').read_text())
def read_lef(ref,path):
 raw=subprocess.check_output(['git','-C',str(ROOT),'show',ref+':'+path]);s=raw.decode();pins={}
 for m in re.finditer(r'  PIN ([^\n]+)\n(.*?)\n  END \1\n',s,re.S):
  r=re.search(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',m[2])
  if r:
   a,b,c,d=map(float,r.groups());pins[m[1]]=((a+c)/2,(b+d)/2)
 return pins,hashlib.sha256(raw).hexdigest()
q,qsha=read_lef('0d4ba50ed','physical/ref_tile/s81dvbk_sq_hq3/views/dsdv_bksel_q/dsdv_bksel_q.lef')
g,gsha=read_lef('cb73b3e99','physical/ref_tile/s81dvbk_g2/views/dsdv_bk_g/dsdv_bk_g.lef')
yq=[43.2,864,1987.2,2764.8];gx,gy=648,1771.2
cx,cy,cs=216,1555.2,388.8
west=205.2;south=1533.6;north=1965.6;east=626.4
bodies=[(216,y,864,y+648)for y in yq]+[(cx,cy,cx+cs,cy+cs),(gx,gy,gx+216,gy+172.8)]
def inside(p):return any(a+1e-6<p[0]<c-1e-6 and b+1e-6<p[1]<d-1e-6 for a,b,c,d in bodies)
md=lambda a,b:abs(a[0]-b[0])+abs(a[1]-b[1])
snap=lambda p:(round(p[0]/.054)*.054,round(p[1]/.270)*.270)
def point(path,t):
 for a,b in zip(path,path[1:]):
  z=md(a,b)
  if t<=z+1e-9:return a if not z else(a[0]+(b[0]-a[0])*t/z,a[1]+(b[1]-a[1])*t/z)
  t-=z
 return path[-1]
rows=[];obstructions=[]
def record(j,kind,bit,path,pin1,pin2,target_port=None,extreme=None):
 length=sum(md(a,b)for a,b in zip(path,path[1:]));ideal=[point(path,length*k/7)for k in range(8)];anchors=[snap(p)for p in ideal]
 for k,p in enumerate(anchors):
  if inside(p):obstructions.append({'q':j,'kind':kind,'bit':bit,'stage':k,'point':p})
 perturb=max(md(a,b)for a,b in zip(anchors,ideal));routed=length/7+2*max(perturb,.162)
 rows.append({'q':j,'kind':kind,'bit':bit,'port':target_port,'extreme':extreme,'route_um':length,'hop_bound_um':routed,'local_pin_um':max(md(pin1,path[0]),md(pin2,path[-1]))})
def endpoint(port,t):
 face=next(f for f,ns in spec['pins'].items()if port in ns);lo,hi=spec['pin_ranges'][port];v=[lo,hi][t]
 if face=='W':return face,(cx,cy+v),(west,cy+v)
 if face=='E':return face,(cx+cs,cy+v),(east,cy+v)
 if face=='S':return face,(cx+v,cy),(cx+v,south)
 return face,(cx+v,cy+cs),(cx+v,north)
def ctrl_path(j,kind,port,rb,wb,face):
 # Macro-free west-spine access; two central status chunks approach the far edge
 # to avoid assuming every signal uses the same narrow horizontal corridor cut.
 if face=='W':return [rb,(west,rb[1]),wb]
 if face=='E':
  central=south if j<2 else north
  return [rb,(west,rb[1]),(west,central),(east,central),wb]
 if face=='S' and j==1:return[rb,(rb[0],south),wb]
 if port=='fs2_0':return[rb,(west,rb[1]),(west,north),(east,north),(east,south),wb]
 if port in ['fs2_1','fs1_2']:return[rb,(west,rb[1]),(west,south),(east,south),(east,north),wb]
 central=south if face=='S' else north
 return[rb,(west,rb[1]),(west,central),wb]
for j in range(4):
 rail=yq[j]+658.8
 def qp(n):x,y=q[n];return(x+216,y+yq[j])
 for b in range(515):
  x,y=g[f'ln{j}[{b}]'];a=(x+gx,y+gy);z=qp(f'lane[{b}]');wb=(gx-10.8 if x<108 else gx+226.8,a[1]);rb=(z[0],rail);central=south if j<2 else north
  path=[wb,(wb[0],central),(rb[0],central),rb]if j==1 else[wb,(wb[0],central),(west,central),(west,rail),rb]
  record(j,'lane',b,path,a,z)
 for kind,width,qn in [('status',865,'t_s'),('command',66,'f_c'),('credit',1,'f_cr'),('selected',354,'t_o')]:
  for b in range(width):
   z=qp(qn if kind=='credit'else f'{qn}[{b}]');rb=(west,z[1])if kind=='selected'else(z[0],rail)
   if kind=='status':port=f'fs{j}_{0 if b<288 else 1 if b<576 else 2}'
   elif kind=='selected':port=f'fo{j}'
   else:port=('t_c_'if kind=='command'else't_cr_')+('s'if j<2 else'n')
   for t in [0,1]:
    face,a,wb=endpoint(port,t);path=ctrl_path(j,kind,port,rb,wb,face)
    record(j,kind,b,path,z,a,port,t)
vd=[];relay=(east,1749.6)
for b in range(514):
 x,y=g[f'vd[{b}]'];z=(x+gx,y+gy)
 for t in [0,1]:
  _,a,_=endpoint('vd',t);vd.append(max(md(a,relay),md(relay,z)))
widths={**{f'fs{j}_{k}':(289 if k==2 else 288)for j in range(4)for k in range(3)},**{f'fo{j}':354 for j in range(4)},'rst_profile':413,'ck':1,'vd':514,'t_c_s':132,'t_c_n':132,'t_cr_s':2,'t_cr_n':2}
faces={f:{'pins':sum(widths[p]for p in ns),'pins_per_um':sum(widths[p]for p in ns)/cs,'capacity_at4':4*cs}for f,ns in spec['pins'].items()}
assert sum(v['pins']for v in faces.values())==6072
assert all(v['pins_per_um']<=4 for v in faces.values())
source_hops=max(x['hop_bound_um']for x in rows)
result={'status':'SOURCE_FACE_INTERVAL_REACH_MODEL_ONLY','quarter_LEF_sha256':qsha,'glue_LEF_sha256':gsha,'outline_um':[cs,cs],'faces':faces,'face_interval_checks':len(rows),'hop_limit_um':405,'max_hop_bound_um':source_hops,'max_local_pin_um':max(x['local_pin_um']for x in rows),'worst':max(rows,key=lambda x:x['hop_bound_um']),'anchor_body_obstructions':len(obstructions),'first_obstructions':obstructions[:12],'reach_bound_met':source_hops<=405 and not obstructions,'VD_one_priced_relay_max_hop_um':max(vd),'VD_relay_point_um':list(relay),'parent':{'outline_um':[907.2,3499.2],'control':[cx,cy,cs,cs],'glue':[gx,gy,216,172.8],'quarter_origins':[[216,y]for y in yq],'north_relay_origin':[129.6,3456],'north_relay_size':[25.92,17.28],'retained_top_band_um':86.4,'growth_vs_old_um':216,'vmtx_band_um':4190.4,'remaining_after_parent_TX540_one_gap43p2_um':108},'unchanged_contract':{'landing_segments_each_direction':7,'landing_edges_each_direction':14,'XR':34,'XD':17,'VD_edges':1,'external_tail_edges':796,'clock_route_period_ps':770,'clock_signoff_period_ps':833.333,'clock_uncertainty_setup_hold_ps':[60,25],'new_pipeline_edges':0},'debts':['Targets are extrema of proposed face intervals, not published new-control pin coordinates.','Anchors are snapped reference points, not allocated landing-cell bodies/fences/pin access/PG/CTS.','Simultaneous routing and actual cut occupancy are unproved; no extra layer grant inferred.','Individual lane/control/return bodies and clock/reset distribution still require actual source-bound parent placement.','Existing fixed source cycles do not prove sustained full-131072 throughput.','TX/VMUX composition and actual complete4190.4 release-band fit remain open.']}
(OUT/'square388_reach.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k]for k in ['status','face_interval_checks','max_hop_bound_um','max_local_pin_um','anchor_body_obstructions','reach_bound_met','VD_one_priced_relay_max_hop_um','worst']},indent=2))
