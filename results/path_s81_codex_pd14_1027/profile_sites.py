#!/usr/bin/env python3
"""Predict physical feasibility of PD13's graded mesh strength before build.
Input geometry is unchanged; each driver site uses baseline count times cap ratio.
This is a placement/cost diagnostic, never routed timing evidence.
"""
import argparse, collections, json, math, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--tools',required=True);p.add_argument('--build',required=True);p.add_argument('--rec',required=True);p.add_argument('--plan',required=True);p.add_argument('--out',required=True);p.add_argument('--legalize',action='store_true');a=p.parse_args()
sys.path.insert(0,a.tools)
import die_clock_mesh as DM, die_clock as DC, schema as S
P=S.Plan(S.load(a.plan),a.plan)
B=Path(a.build);M=json.load(open(B/'mesh.json'));R=json.load(open(a.rec));C=json.load(open(B/'place.json'))
rx,ry=R['root_xy'];wmax=128;half=4000
wq=lambda d:4 if d>=half else max(4,int(round((4+(wmax-4)*(1-d/half))/4))*4)
cf=lambda w:.9+.0875*w
rows=[];new={k:dict(v) for k,v in C.items() if v['kind']!='drv'}
base_count=0;new_count=0
K=DC.KeepIndex(DC.keepouts(P),die=(P.W,P.H)); occupied=collections.defaultdict(list)
def reserve(c):
 x,y=c['x'],c['y'];r=(x,y,x+DM.cell_width(c),y+DM.ROW_Y)
 for i in range(math.floor(r[0]/40),math.floor(r[2]/40)+1):
  for j in range(math.floor(r[1]/40),math.floor(r[3]/40)+1):occupied[i,j].append(r)
def clear(c):
 x,y=c['x'],c['y'];r=(x,y,x+DM.cell_width(c),y+DM.ROW_Y)
 if not(0<=r[0]<r[2]<=P.W and 0<=r[1]<r[3]<=P.H):return False
 for i in range(math.floor(r[0]/K.b),math.floor(r[2]/K.b)+1):
  for j in range(math.floor(r[1]/K.b),math.floor(r[3]/K.b)+1):
   for b in K.g.get((i,j),[]):
    if min(r[2],b[2])-max(r[0],b[0])>1e-5 and min(r[3],b[3])-max(r[1],b[1])>1e-5:return False
 for i in range(math.floor(r[0]/40),math.floor(r[2]/40)+1):
  for j in range(math.floor(r[1]/40),math.floor(r[3]/40)+1):
   for b in occupied.get((i,j),[]):
    if min(r[2],b[2])-max(r[0],b[0])>1e-5 and min(r[3],b[3])-max(r[1],b[1])>1e-5:return False
 return True
for c in new.values():reserve(c)
legalize_fail=[];shifts=[]
def cluster(x,y,count,cols):
 nr=math.ceil(count/cols)
 return [dict(x=DM.snap(x+(j%cols-(cols-1)/2)*DM.BUF_W-DM.BUF_W/2,DM.SITE_X),y=DM.snap(y-nr*DM.ROW_Y/2,DM.ROW_Y)+(j//cols)*DM.ROW_Y,kind='drv') for j in range(count)]
for key,d in M['drivers'].items():
 x,y=d['site'];width=max(wq(abs(x-rx)),wq(abs(y-ry)));k=max(1,round(cf(width)/cf(4)));base=len(d['cells']);count=base*k
 base_count+=base;new_count+=count
 rows.append(dict(site=key,xy_um=[x,y],width_multiple=width,base_cells=base,new_cells=count,input_cap_ratio=k))
 picked=cluster(x,y,count,count);move=0.0
 if a.legalize:
  found=False
  # Clock geometry remains on the same strap axis. Full cell bodies are checked before accepting.
  for step in range(742):
   if found:break
   for sign in ([1] if step==0 else [1,-1]):
    shift=sign*step*DM.ROW_Y; xx=x+(shift if d['strap']=='M8' else 0); yy=y+(shift if d['strap']=='M9' else 0)
    for cols in sorted({count,max(1,math.ceil(count/2)),max(1,math.ceil(count/4)),max(1,math.ceil(math.sqrt(count)))},reverse=True):
     cells=cluster(xx,yy,count,cols)
     if all(clear(c) for c in cells):picked=cells;move=abs(shift);found=True;break
    if found:break
  if not found:legalize_fail.append(key)
 shifts.append(move);rows[-1]['slide_um']=move;rows[-1]['cell_rects_um']=[[c['x'],c['y'],c['x']+DM.BUF_W,c['y']+DM.ROW_Y] for c in picked]
 for j,c in enumerate(picked):new[f'profile_{key}_{j}']=c;reserve(c)
bad=DM.hard_keepout_violations(P,new)
# Exact cell body overlaps using narrow spatial bins, report separately from keepouts.
grid=collections.defaultdict(list);over=[]
for name,c in new.items():
 x,y=c['x'],c['y'];w=DM.cell_width(c);r=(x,y,x+w,y+DM.ROW_Y)
 keys=[(i,j) for i in range(math.floor(x/2),math.floor((x+w)/2)+1) for j in range(math.floor(y/1),math.floor((y+DM.ROW_Y)/1)+1)]
 seen=set()
 for g in keys:
  for n,s in grid[g]:
   if n in seen:continue
   seen.add(n)
   if min(r[2],s[2])-max(r[0],s[0])>1e-5 and min(r[3],s[3])-max(r[1],s[1])>1e-5:over.append([name,n])
 for g in keys:grid[g].append((name,r))
out=dict(schema='opentallas.s81.profile_site_prediction.v1',kind='PREDICTION_ONLY',profile=dict(mesh_peak_w=128,half_band_um=4000,strength='baseline_mult * round(local_cap/base_cap)'),drivers=len(rows),strengthened_sites=sum(r['new_cells']>r['base_cells'] for r in rows),legalize=a.legalize,legalize_fail=legalize_fail,moved_sites=sum(x>0 for x in shifts),max_slide_um=max(shifts),baseline_bufx24=base_count,new_bufx24=new_count,added_bufx24=new_count-base_count,added_buf_area_um2=(new_count-base_count)*DM.BUF_W*DM.ROW_Y,max_cells_per_site=max(r['new_cells'] for r in rows),max_site_width_um=max(r['new_cells'] for r in rows)*DM.BUF_W,keepout_violations=len(bad),overlap_pairs=len(over),violations=bad,overlaps=over,sites=rows,limitations=['Upper-tree x3 cells not resized here.','Added mesh-driver input capacitance must be included in upstream tree prediction.','Slew/EM/IR and 405um repeater site census remain required.','Existing PD13 diagnostic counted added cells without baseline m=2; corrected physical count here.'])
Path(a.out).write_text(json.dumps(out,indent=1)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('sites','violations','overlaps','limitations')}))
