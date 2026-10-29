import json,sys,matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
A=json.load(open(sys.argv[1]));B=json.load(open(sys.argv[2]));H=4.32
fig,ax=plt.subplots(2,2,figsize=(22,16))
for col,tn in enumerate(['q_hub_nw','q_hub_ne']):
  for row,(P,lab) in enumerate([(A,'before c25c_d14'),(B,'after c25c_d15 station_resite')]):
    t=P['partition_types'][tn];a=ax[row][col];R=[]
    for h in t['hard_cores']:
      (x,y),(w,hh)=h['origin_um'],h['outline_um'];R.append((x-H,y-H,x+w+H,y+hh+H))
      a.add_patch(Rectangle((x,y),w,hh,fc='#dde',ec='#446',lw=.5))
    ins=[];out=[]
    for s in t['internal_stations']:
      for r in s.get('regs_um',[]):
        (ins if any(x0<r[0]<x1 and y0<r[1]<y1 for x0,y0,x1,y1 in R) else out).append(r)
    if out: a.scatter(*zip(*out),s=1,c='#2a2')
    if ins: a.scatter(*zip(*ins),s=3,c='red')
    W,Hh=t['outline_um'];a.set_xlim(0,W);a.set_ylim(0,Hh);a.set_aspect('equal')
    a.set_title(f'{tn} {lab}: station regs in core body+halo = {len(ins)} (red), legal {len(out)} (green)')
plt.tight_layout();plt.savefig(sys.argv[3],dpi=70)
