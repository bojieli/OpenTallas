from pathlib import Path
import json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).parent;p=json.load(open(R/'source_homes_candidatePG.json'));plan=json.load(open(R/'authoritative_plan.json'));overlay=json.load(open(R/'candidate_pg_overlay.json'));lib=json.load(open(R/'library_all.json'))['cell_library']
fig,axs=plt.subplots(1,3,figsize=(19,7))
a=axs[0]
for part in plan['partitions']:
 x,y=part['origin_um'];w,h=plan['partition_types'][part['type']]['outline_um'];a.add_patch(Rectangle((x,y),w,h,fill=False,edgecolor='.8',linewidth=.3))
for g in p['groups']:
 x,y,X,Y=g['rect_um'];a.plot(x,y,'.',ms=3,color='red'if'MODEL'in g['clock_source']else'navy')
a.set_title('All174source islands /3149actual mapped cells\nred=new MODEL clock nodes; blue=old clock source');a.autoscale();a.set_aspect('equal');a.set_xlabel('global um');a.set_ylabel('global um')
a=axs[1]
for o in overlay['changes']:
 x,y,X,Y=o['old'];a.add_patch(Rectangle((x,y),X-x,Y-y,fill=False,edgecolor='orange',linestyle='--',label='oldPG'if o==overlay['changes'][0]else None))
 x,y,X,Y=o['candidate_model_only'];a.add_patch(Rectangle((x,y),X-x,Y-y,facecolor='lightgray',edgecolor='gray',alpha=.6,label='candidateA PG exclusion'if o==overlay['changes'][0]else None))
for g in p['groups']:
 x,y,X,Y=g['rect_um']
 if 23000<x<29000 and y<1450:a.plot([x,X,X,x,x],[y,y,Y,Y,y],color='navy',lw=1)
a.set_xlim(23000,29100);a.set_ylim(100,1450);a.set_title('ES0/ES1candidate-only PG exclusion overlay\noldPG caused11genuine source-tile failures');a.set_xlabel('global um');a.legend(fontsize=7);a.set_aspect('equal')
records=[s for s in p['source_records']if s.get('signal')=='raw'and'output_sinks_homes'in s]
s=max(records,key=lambda s:sum(t.get('direct_point_distance_um',0)for t in s['output_sinks_homes']if t.get('master')=='AND2x2_ASAP7_75t_R'))
g=next(g for g in p['groups']if g['region']==s['region']);x,y,X,Y=g['rect_um'];a=axs[2]
for n,c in p['cells'].items():
 xx,yy=c['xy_um']
 if x-1e-5<=xx<X and y-1e-5<=yy<Y:
  w,h=lib[c['master']]['size_um'];kind=c['master'];color='royalblue'if kind.startswith('DFF')else'orange'if kind.startswith('INV')else'green'if kind.startswith('BUF')else'purple'
  a.add_patch(Rectangle((xx-x,yy-y),w,h,edgecolor='black',facecolor=color,alpha=.5,linewidth=.3))
  a.text(xx-x+w/2,yy-y+h/2,kind.split('_')[0],fontsize=4,rotation=90,ha='center',va='center')
sx,sy=s['output_pin_um']
for t in s['output_sinks_homes']:
 if t.get('master')in ['AND2x2_ASAP7_75t_R','BUFx2_ASAP7_75t_R']and'pin_um'in t:
  tx,ty=t['pin_um'];a.plot([sx-x,tx-x,tx-x],[sy-y,sy-y,ty-y],lw=.6,color='red')
a.set_xlim(-.1,8.74);a.set_ylim(-.1,.91);a.set_title('Worst RAW local-reset island: ACTUAL full cell footprints\n3AND2x2+B​UF2 loads retained /point routes only');a.set_xlabel('tile-local um');a.set_ylabel('tile-local um');a.set_aspect('equal')
fig.suptitle('Source preparation only: QN→INV max0.190um /source-cell→clockpoint max9.288um\nNO native functional STD occupancy, actual clock binding, PG/routed-access, STA or physical admission',fontsize=12)
fig.tight_layout();fig.savefig(R/'source_homes_review.png',dpi=180)
