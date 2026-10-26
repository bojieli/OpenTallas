import json,sys,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
p=Path('/srv/opentallas-scratch/claude/codex-qc-sramif-1713');fig,axs=plt.subplots(1,2,figsize=(18,8))
for ax,k in zip(axs,('btab','prog')):
 j=json.loads((p/(k+'_profile.json')).read_text());pins=json.loads((p/(k+'_pins.json')).read_text());W,H=j['outline_um']
 ax.add_patch(plt.Rectangle((0,0),W,H,fill=False,color='black'))
 for m in j['macro_sites']:
  x,y,w,h=m['x'],m['y'],m['w'],m['h'];ax.add_patch(plt.Rectangle((x-4.32,y-4.32),w+8.64,h+8.64,fill=False,color='orange',linewidth=1));ax.add_patch(plt.Rectangle((x,y),w,h,color='gray',alpha=.5));ax.text(x+w/2,y+h/2,m['master'].split('_')[4],ha='center',fontsize=8)
  for xx in (x-12,x+w+12):ax.plot(xx,y+20.52,'ro',markersize=4)
 for i in range(4):ax.plot((i+.5)*W/4,16,'ro',markersize=4)
 ax.plot(177.132,6,'ks',markersize=6)
 for face,col in (('S','seagreen'),('E','royalblue')):
  ps=[z for z in pins if z['face']==face];ax.scatter([z['x'] for z in ps],[z['y'] for z in ps],s=2,color=col)
 ax.axhspan(4.32,25.92,color='seagreen',alpha=.08)
 ax.text(4,248,'Halos4.32um; red=planned regional taps; green=input banks',fontsize=7)
 ax.set(xlim=(-4,W+4),ylim=(-4,H+4),title=f'{k.upper()} NEW R0 354.24x259.2; {len(pins)} native ports\nSame RTL / +0 cycles; new pins, shorter macro column / 12 clock banks',xlabel='um',ylabel='um');ax.set_aspect('equal')
fig.tight_layout();fig.savefig(p/'aspect1713_plan.png',dpi=140)
