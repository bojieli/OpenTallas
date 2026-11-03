import json
from pathlib import Path
p=Path(__file__).parent;d=json.load(open(p/'audit_guides.json'))
proposal=[('M1',[185.25,164.16,185.82,164.73]),('M2',[185.25,164.16,189.24,164.73]),('M3',[188.67,164.16,189.24,166.44]),('M2',[188.67,165.87,224.58,166.44]),('M3',[224.01,164.16,224.58,166.44]),('M2',[224.01,164.16,229.14,164.73]),('M1',[228.57,164.16,229.14,164.73])]
json.dump({'status':'UNRUN_GUIDE_ONLY_PREP','net':r'u_u_rsq1.u_rsq.g_nr\[0\].g_h.d_h.genblk1.g_line.line\[238\]','guides':[{'layer':l,'bbox':b} for l,b in proposal],'scope':'Exact single SIGNAL guide correction; no metal/pose/source/clock edits; native route and DRC required','macro_body':d['macro']['bbox']},open(p/'proposed_guides.json','w'),indent=2)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(13,5))
for name,rows,c,a in [('old',d['guides'],'red',.17),('proposed',[{'layer':l,'bbox':b} for l,b in proposal],'green',.25)]:
 for q in rows:
  x,y,X,Y=q['bbox'];ax.add_patch(Rectangle((x,y),X-x,Y-y,color=c,alpha=a));ax.text((x+X)/2,(y+Y)/2,q['layer'],fontsize=7,color=c)
x,y,X,Y=d['macro']['bbox'];ax.add_patch(Rectangle((x,y),X-x,Y-y,fill=False,edgecolor='black',lw=2));ax.text(202,164.7,'Actual SRAM body',fontsize=10)
ax.set(xlim=(184,231),ylim=(163.8,166.9),xlabel='x (um)',ylabel='y (um)',title='Single-net guide PREP: old red corners intersect macro; green ascent/descent outside body')
ax.grid(alpha=.2);fig.tight_layout();fig.savefig(p/'proposed_guides.png',dpi=160)
