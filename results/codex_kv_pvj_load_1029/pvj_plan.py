import json,re
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
p=Path('/srv/opentallas-scratch/claude/wt/codex-kv-pvj-load-1029/results/codex_kv_pvj_load_1029')
pins=json.load(open(p/'current24/cores/pv_join_pins_r26q5c_de688492fadf.json'))['pins']
f,ax=plt.subplots(figsize=(9,9));ax.add_patch(plt.Rectangle((0,0),172.8,172.8,fill=False,lw=2))
for kind,color in [('ts','#a5b8cd'),('y','#e39337'),('clk','#e52937'),('rst','#b029ce')]:
 q=[q for q in pins if q['name'].startswith(kind)]
 ax.scatter([q['x'] for q in q],[q['y'] for q in q],s=7 if kind in ['ts','y'] else 60,c=color,label=kind+' pins')
for g in range(32):
 q=[q for q in pins if re.fullmatch(r'y\[(\d+)\]',q['name']) and int(re.search(r'\d+',q['name'])[0])//16==g]
 if q:
  x=sum(a['x'] for a in q)/len(q);y=sum(a['y'] for a in q)/len(q)
  px=154 if x>86.4 else 18;py=max(9,min(164,y));ax.plot([x,px],[y,py],color='#de8b23',alpha=.4)
  ax.scatter([px],[py],marker='s',s=70,facecolors='white',edgecolors='#a65d0a');ax.text(px,py,str(g),fontsize=5,ha='center',va='center')
ax.text(86,115,'Macro-free join body\n15,939 existing FF + 32 local load FF\n32 groups × 16 output bits\n0 added cycles; same golden arithmetic',ha='center',fontsize=10)
ax.text(86,52,'Squares show intended output-local ownership,\nnot fixed placements. Exact mapped names/count checked.\nClock: same central entry / current24 trunk.\nSource 850fa6e8a; current24 canonical pins.',ha='center',fontsize=9)
ax.set(xlim=(-12,185),ylim=(-12,185),xlabel='x (µm)',ylabel='y (µm)',title='PVJ R0 source placement plan — review before place')
ax.legend(loc='upper center',fontsize=8);ax.set_aspect('equal');f.tight_layout();f.savefig(p/'PVJ_LOAD_PLAN.png',dpi=150)
