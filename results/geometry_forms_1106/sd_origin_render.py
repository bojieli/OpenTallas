import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
base=Path(__file__).resolve().parent
a=json.loads((base/'sd_origin_actual.json').read_text());c=json.loads((base/'sd_origin_candidate.json').read_text())
fig,axs=plt.subplots(3,1,figsize=(15,10),gridspec_kw={'height_ratios':[2,1,1]})
for ax in axs:
 for q in a['macros']:
  x,y,X,Y=q['rect'];ax.add_patch(Rectangle((x,y),X-x,Y-y,color='#c5cbd2',alpha=.7))
 for q in a['origin']:
  x,y,X,Y=q['rect'];ax.plot((x+X)/2,(y+Y)/2,'.',color='#b33b36',ms=3)
 for p in c['hop_paths_um']:
  ax.plot([q[0] for q in p],[q[1] for q in p],color='#177f42',lw=1.5)
 pts=c['points_um']+[c['proposed_s2_um']]
 for j,(x,y) in enumerate(pts):ax.plot(x,y,'o',color='#177f42',ms=5)
 ax.set_aspect('equal');ax.grid(alpha=.2);ax.set_xlabel('x (um)');ax.set_ylabel('y (um)')
axs[0].set(xlim=(0,1900.8),ylim=(0,1036.8),title='SYS_SD actual GRT origin in red; proposed complete START chain in green')
axs[0].text(850,550,'PHY macro: M1-M5 obstruction',ha='center')
axs[1].set(xlim=(140,1900),ylim=(0,70),title='Bottom corridor: two added START bundle stages, then existing s0 and s1')
for j,(x,y) in enumerate(c['points_um']):axs[1].annotate(['NEW0','NEW1','s0','s1'][j],(x,y),xytext=(0,13),textcoords='offset points',ha='center')
axs[2].set(xlim=(1845,1900),ylim=(100,205),title='East corridor: retain existing s2/pd stages; proposed sites clear macro and reservations')
for name,p in [('s2',c['proposed_s2_um']),('pd',c['proposed_pd_um'])]:axs[2].annotate(name,p,xytext=(10,0),textcoords='offset points');axs[2].plot(*p,'o',color='#177f42',ms=5)
fig.text(.02,.01,'Planning candidate only. Actual full path 1846.05 um; maximum planned hop 369.252 um; +2 boot cycles. Clock source offsets remain real semantics.',fontsize=10)
fig.tight_layout(rect=(0,.03,1,1));fig.savefig(base/'sd_origin_review.png',dpi=150)
