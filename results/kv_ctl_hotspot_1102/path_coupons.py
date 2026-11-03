"""Real endpoint road coupons; not local pin-access or signal-routing closure."""
import json,gzip,sys,math,inspect,re,csv,os,collections
from pathlib import Path
import numpy as np
O=Path(__file__).resolve().parent;code=(O/'trace_hotspots.py').read_text().split('allnets=D.nets;boxmap=[]')[0];exec(compile(code,str(O/'trace_hotspots.py'),'exec'))
guides=json.loads(gzip.decompress((O/'comb_road_model.json.gz').read_bytes()));gm={p['name']:p for p in guides['cells']};ids={c[6]:i for i,c in D.cells.items()}
for n,p in gm.items():
 i=ids[n];c=D.cells[i];x,y=p['ll_dbu'];w,h=p['size_dbu'];D.cells[i]=tuple(list(c[:2])+[x/1000,y/1000,(x+w)/1000,(y+h)/1000]+list(c[6:]));ff[n]=p
hot=json.loads(gzip.decompress((O/'hotspot_contributors.json.gz').read_bytes()));tracks={q['layer']:q for q in json.load(open(C/'tracks.json'))['tracks']};tx=np.array(tracks['M5']['X']);tx=tx[(tx>=8640)&(tx<241920)]-8640
# Full-pitch clearance beyond half of the largest observed VIA45 PG landing,
# rounded upward to three M5 grid pitches; no new via is instantiated.
blocked=[]
for b in std['M5']:blocked.append([b[0]-8640-108,b[2]-8640+108])
for b in extra.get('M5',[]):blocked.append([b[0]-108,b[2]+108])
free=np.ones(len(tx),bool)
for a,b in blocked:free &= ~((tx>=a)&(tx<=b))
free_x=tx[free]/1000;assert len(free_x)>1000
sy=np.array([y for y in tracks['M4']['Y'] if 4320<=y<12960]);all_h=np.concatenate([sy+k*8640 for k in range(-1,36)])/1000;all_h=all_h[(all_h>=4.32)&(all_h<298.08)]

def h_track(target,x0,x1,y0,y1):
 candidates=all_h[(all_h>y0)&(all_h<y1)];candidates=candidates[np.argsort(abs(candidates-target))]
 for y in candidates:
  if 146.68<=y<=155.72 and min(x0,x1)<121.16 and max(x0,x1)>112.12:continue
  if any(m[3]-.060<=y<=m[5]+.060 and min(x0,x1)<m[4]+.060 and max(x0,x1)>m[2]-.060 for m in mm):continue
  rep=4320+((y*1000-8640-4320)%8640);rs=std['M4'];bad=(rs[:,0]-24<max(x0,x1)*1000+8640)&(rs[:,2]+24>min(x0,x1)*1000+8640)&(rs[:,1]-24<rep)&(rs[:,3]+24>rep)
  if not bad.any():return float(y)
 raise ValueError(('NO_M4_ROAD_TRACK',target,x0,x1,y0,y1))
def nearest_col(x):return float(free_x[np.argmin(abs(free_x-x))])
def endpoint(e):
 w=access_windows(e);q=w[0];return dict(instance=e['inst'],pin=e['pin'],layer=q[4],xy=[(q[0]+q[2])/2,(q[1]+q[3])/2],window_um=q[:4])
result=[]
for direction in ['H','V']:
 picked=None
 for q in next(w for w in hot['windows'] if w['direction']==direction)['contributors']:
  if q['clock_network']:continue
  n=native[q['index']]
  if len(n['drivers'])!=1:continue
  dr=n['drivers'][0]
  if dr['inst'] is None or D.cells[G.ref(dr['ref'])[1]][0]!='S':continue
  for sk in n['sinks']:
   if sk['inst'] not in gm:continue
   if gm[sk['inst']]['zone'].startswith(direction):
    a,b=endpoint(dr),endpoint(sk)
    if direction=='H' and not min(a['xy'][0],b['xy'][0])<77.5<max(a['xy'][0],b['xy'][0]):continue
    if direction=='V' and not min(a['xy'][1],b['xy'][1])<147.5<max(a['xy'][1],b['xy'][1]):continue
    picked=(q,n,a,b);break
  if picked:break
 assert picked, direction
 q,n,a,b=picked;ax,ay=a['xy'];bx,by=b['xy'];ac,bc=nearest_col(ax),nearest_col(bx)
 if direction=='H':
  yh=h_track(283.,ac,bc,269.73,298.08);points=[[ax,ay],[ac,ay],[ac,yh],[bc,yh],[bc,by],[bx,by]];layers=['LOCAL_ACCESS_OPEN','M5','M4','M5','LOCAL_ACCESS_OPEN'];trunk=dict(layer='M4',y_um=yh,crosses_old_cut_at=[77.5,yh],outside_old_window=not 256<=yh<=266)
 else:
  available=free_x[(free_x>123.12)&(free_x<151.2)];vx=float(available[np.argmin(abs(available-135.))]);ya=h_track(ay,ac,vx,155.72 if ay>147.5 else 4.32,298.08 if ay>147.5 else 146.68);yb=h_track(by,bc,vx,155.72 if by>147.5 else 4.32,298.08 if by>147.5 else 146.68);points=[[ax,ay],[ac,ay],[ac,ya],[vx,ya],[vx,yb],[bc,yb],[bc,by],[bx,by]];layers=['LOCAL_ACCESS_OPEN','M5','M4','M5','M4','M5','LOCAL_ACCESS_OPEN'];trunk=dict(layer='M5',x_um=vx,crosses_old_cut_at=[vx,147.5],outside_old_window=not 99<=vx<=109)
 length=sum(abs(p[0]-s[0])+abs(p[1]-s[1]) for p,s in zip(points,points[1:]));direct=abs(ax-bx)+abs(ay-by);result.append(dict(direction=direction,native_net_id=n['native_id'],native_net_index=n['index'],native_net_name=n['name'],driver=a,sink=b,segments=[dict(layer=l,start=p,end=s) for l,p,s in zip(layers,points,points[1:])],trunk=trunk,path_length_um=length,endpoint_Manhattan_um=direct,extra_road_length_um=length-direct,status='METAL_ROAD_PG_OBS_COUPON_NOT_ACTUAL_SIGNAL_ROUTE',local_pin_access_and_via_stack='OPEN_NORMAL_ROUTER',signal_signal_packing='OPEN_NORMAL_ROUTER'))
r=dict(status='SOURCE_PIN_ROAD_COUPONS_ONLY',global_M5_columns_with_derived_landing_clearance=len(free_x),M5_OBS_in_actual_SRAM_master=sorted(x for x in D.extra['mobs']['ctl_sram_1r1w_64x128_p192'] if x=='M5'),paths=result,limits=['Real endpoint windows come from immutable native master shapes; selected existing comb cells use modeled guide sites','Metal trunks avoid macro OBS and source-phase PG and leave the old hotwindow; source clock bay bypassed','No local M1 pin-access/via-stack closure, route claim, threshold waiver or cells inserted'])
(O/'road_path_coupons.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
