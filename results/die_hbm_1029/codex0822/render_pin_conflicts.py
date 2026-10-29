import json,sys,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
src=Path(sys.argv[1]);r=json.load(open(src/'die_plan.repin.json'));old=json.load(open(src/'die_plan.json'));rep=json.load(open(src/'pin_conflicts_report.json'));fig,axs=plt.subplots(3,3,figsize=(15,12));seen=set()
for ax,c in zip(axs.flat,rep['changes']):
 h=next(h for h in r['partition_types'][c['type']]['hard_cores'] if h['inst']==c['inst']);o=next(h for h in old['partition_types'][c['type']]['hard_cores'] if h['inst']==c['inst']);W,H=h['outline_um'];before={p['name']:p for p in json.load(open(src/o['pins_file']))};after=json.load(open(src/h['pins_file']));changed=[p for p in after if (p['layer'],p['x'],p['y'])!=(before[p['name']]['layer'],before[p['name']]['x'],before[p['name']]['y'])]
 assert len(after)==len(before) and set(before)=={p['name'] for p in after}
 ax.plot([0,W,W,0,0],[0,0,H,H,0],color='black');ax.scatter([p['x'] for p in after],[p['y'] for p in after],s=1,c='gray');ax.scatter([p['x'] for p in changed],[p['y'] for p in changed],s=3,c='red');ax.scatter([before[p['name']]['x'] for p in changed],[before[p['name']]['y'] for p in changed],s=2,c='blue');ax.set_title(c['type']+' '+c['inst']+'\n'+str(len(changed))+' moved data pins',fontsize=9);ax.set_aspect('equal');ax.set_xlim(-8,W+8);ax.set_ylim(-8,H+8)
plt.tight_layout();plt.savefig(sys.argv[2],dpi=130)
