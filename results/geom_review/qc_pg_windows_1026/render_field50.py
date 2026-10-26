from pathlib import Path
import json,math
import matplotlib.pyplot as plt
R=Path(__file__).parent;d=json.loads((R/'field50/bumps.json').read_text());x0,y0,x1,y1=d['rect_um'];fig,axs=plt.subplots(1,2,figsize=(13,7),layout='constrained')
for j,ax in enumerate(axs):
 for q in d['sites']:
  if j==0 and not q['published']:continue
  x,y=q['xy_um'];color='#b62b2b'if q['role']=='POWER'else'#202020'if q['role']=='GND'else'#2c79ab'if q['name'].startswith('rx')else'#d49a18'
  if q['published']:ax.scatter(x-x0,y-y0,c=color,s=28,marker='o',zorder=3)
  else:ax.scatter(x-x0,y-y0,edgecolors=color,facecolors='none',s=50,marker='s',linewidths=1.4,zorder=4)
 ax.set(xlim=(0,x1-x0),ylim=(0,y1-y0),aspect='equal',xlabel='Field x (um)',ylabel='Field y (um)',title='Published 16-column template:240 sites'if j==0 else'Only74 vacant sites gain PG:314 sites')
 ax.grid(alpha=.15)
fig.suptitle('UCIe PG prototype: published signal/control/ground positions retained\n777.6um field,45um hex lattice,32GT/s,2.4576W; extra39 supply+35 ground →79 supply+79 ground+156 signal/control\nFilled dots=original positions; open squares=extra PG; 16-column map at45um is outside its25–37um shoreline optimum')
fig.savefig(R/'ucie_field50_review.png',dpi=155)
p=d['sites'];m=min(math.dist(a['xy_um'],b['xy_um'])for i,a in enumerate(p)for b in p[i+1:]);print('minimum site separation',m,'um')
