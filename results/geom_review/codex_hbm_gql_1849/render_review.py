import csv,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p='/srv/opentallas-scratch/claude/codex-hbm-gql-1849/'
fig,axs=plt.subplots(1,2,figsize=(12,5))
for ax in axs:
 for r in csv.DictReader(open(p+'placed.csv')):
  if r['kind'] in ('pin','tap'):continue
  x,y,w,h=map(float,(r['x'],r['y'],r['w'],r['h']))
  if ax is axs[1] and not (60<x<78 and 96<y<111): continue
  if ax is axs[0] and hash(r['name']) % 20: continue
  ax.add_patch(Rectangle((x,y),w,h,facecolor='#85a4b5',alpha=.45,lw=.1))
 ax.add_patch(Rectangle((64.8,99.36),8.64,8.64,facecolor='none',edgecolor='purple',lw=1.5))
 for name,y in [('clock',105.84),('reset',101.52)]:
  for x in [66.96,71.28]:ax.plot(x,y,'rx',ms=8)
  for x in [68.04,70.2]:ax.plot(x,y,'go',ms=5)
 ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um')
axs[0].set_xlim(0,142.56);axs[0].set_ylim(0,207.36);axs[0].set_title('Reviewed density26 placement retained')
axs[1].set_xlim(62,76);axs[1].set_ylim(97,110);axs[1].set_title('Island: old red x, proposed green pins')
fig.tight_layout();fig.savefig(p+'review.png',dpi=140)
