import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
B=Path(__file__).parent;x=json.loads((B/'model.json').read_text());p=json.loads((B/'inputs/mu6_plan.json').read_text());fig,axs=plt.subplots(1,3,figsize=(17,7))
a=axs[0]
for b in p['blocks']:
 if b['name'] not in ['bk_sel','seqhost','s_4S','s_4N']:continue
 a.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='#bdd3e9',edgecolor='black'));a.text(b['x']+b['w']/2,b['y']+b['h']/2,b['name'],ha='center',va='center',fontsize=9,clip_on=True)
a.set_xlim(17350,18700);a.set_ylim(9500,17400);a.set_aspect('equal');a.tick_params(axis='x',labelrotation=45,labelsize=7);a.set_title('Frozen mu6 parent neighbors\n499.219 µm gap to seqhost')
a=axs[1];r=x['topk']['options'][1];box=r['parent_box'];W,H=box['w'],box['h'];a.add_patch(Rectangle((0,0),W,H,fill=False,linewidth=2))
for i in range(4):
 y=43.2+i*(648+43.2);a.add_patch(Rectangle((43.2,y),648,648,facecolor='#9acdc2',edgecolor='black'));a.text(367.2,y+324,f'q{i}\n648×648 R0',ha='center',va='center',fontsize=8)
cy=4*648+3*43.2+2*43.2
for name,xx,ww in [('u_c',43.2,388.8),('u_g',475.2,172.8)]:
 a.add_patch(Rectangle((xx,cy),ww,172.8,facecolor='#f5dca6',edgecolor='black'));a.text(xx+ww/2,cy+86.4,name,ha='center',va='center',fontsize=9)
a.annotate('fixed credit loop\n5144-bit upper trunk\nvs 1860 raw-budget\nNO added edges admitted',xy=(820,2100),xytext=(1100,2100),arrowprops=dict(arrowstyle='->',color='red'),color='red',fontsize=9)
a.set_xlim(-100,2200);a.set_ylim(-50,H+300);a.set_aspect('equal');a.set_title('907.2×3283.2 area/geometry candidate\nREFUSED: credit, clock, track, 100 µm gap')
a=axs[2]
for b in p['blocks']:
 if b['kind'] not in ['frame','slice','ctrl','phy']:continue
 if b['x']+b['w']<8000 or b['x']>24000 or b['y']>8000:continue
 a.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='#ddd',edgecolor='#999',linewidth=.4))
for b in x['svc']['new_boxes']:
 a.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='#e9b0a2',edgecolor='darkred',alpha=.8));a.text(b['x']+b['w']/2,b['y']+b['h']/2,b['name'][4:],ha='center',va='center',fontsize=7)
for b in x['svc']['reader_boxes']:
 a.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor='#acbfe5',edgecolor='navy',alpha=.9))
a.set_xlim(7800,24200);a.set_ylim(0,8000);a.set_aspect('equal');a.set_title('SVC 1728×1641.6 + idx3 overlay\nOriginal array: collisions, not an adoption')
for a in axs:a.set_xlabel('µm');a.set_ylabel('µm');a.grid(alpha=.15)
fig.suptitle('S81 next-die composition — MODEL ONLY / NOT A SELECTED FULL MAP',fontsize=15);fig.tight_layout();fig.savefig(B/'composition_model.png',dpi=160)
