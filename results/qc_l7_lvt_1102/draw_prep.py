from pathlib import Path
import json,csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).parent;d=json.load(open(p/'MODEL_PREP.json'));rows=list(csv.DictReader(open('/srv/opentallas-scratch/claude/codex-qc62-collect-1101/l7_final_placed.csv')));fig,axs=plt.subplots(1,4,figsize=(18,4.5))
for ax,t in zip(axs,d['targets']):
 x,y,X,Y=t['bbox_um'];cx=(x+X)/2;cy=(y+Y)/2
 for r in rows:
  a,b,w,h=map(float,[r['x'],r['y'],r['w'],r['h']])
  if a>cx+3 or a+w<cx-3 or b>cy+1.5 or b+h<cy-1.5:continue
  color='#d1428a' if r['name']==t['name'] else '#4a84b4' if r['kind']=='ff' else '#e1e5e8';ax.add_patch(Rectangle((a,b),w,h,facecolor=color,edgecolor='white',lw=.35))
 ax.annotate(t['name']+' RVT→LVT',(cx,cy),xytext=(cx+.5,cy+.8),arrowprops={'arrowstyle':'-','color':'#90164f'},fontsize=8)
 ax.set(xlim=(cx-3,cx+3),ylim=(cy-1.5,cy+1.5),xlabel='x (um)',ylabel='y (um)',title=t['old'].replace('_ASAP7_75t_R','')+f' {t["orient"]}');ax.set_aspect('equal')
fig.suptitle('L7 PREP: four existing DATA AND cells, exact current boxes/orientations\nSame truth function, routing PIN/OBS/site/bbox/area; no source/pose/clock/state/cycle changes',fontsize=11);fig.tight_layout();fig.savefig(p/'candidate_prep.png',dpi=170)
