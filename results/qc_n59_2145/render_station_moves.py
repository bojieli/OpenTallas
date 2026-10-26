import json,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=json.load(open(sys.argv[1]));m=json.load(open(sys.argv[2]));fig,ax=plt.subplots(figsize=(12,8))
for a,b,c,d in p['macros']:ax.add_patch(Rectangle((a,b),c-a,d-b,facecolor='#ccc',edgecolor='#777'))
colors={'f_dd':'#1578a8','dr_o':'#bf5036','pd':'#32864f','f_lcv':'#752e9a','s1_w4':'#bd8b11'}
for group,color in colors.items():
 rows=[r for r in m['stations'] if r['group']==group]
 if not rows:continue
 x,y=zip(*(r['xy_um'] for r in rows));ax.scatter(x,y,s=8,c=color,label=f'{group}: {len(rows)}, max {m["summary"][group]["max_hop_um"]:.1f}um')
 for r in rows[::max(1,len(rows)//20)]:
  x0,y0=r['original_xy_um'];x1,y1=r['xy_um'];ax.plot([x0,x1],[y0,y1],color=color,lw=.4,alpha=.35)
ax.set_xlim(0,777.6);ax.set_ylim(0,518.4);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um')
ax.set_title('N59 zero-cycle station proposal — pending batch1 dr_o window; no P&R verdict')
ax.legend(loc='upper center',bbox_to_anchor=(.5,-.12),ncol=3)
fig.tight_layout();fig.savefig(sys.argv[3],dpi=140)
