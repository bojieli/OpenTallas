from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b=Path(__file__).parent;d=json.loads((b/'whole_kv_bridge_candidate.json').read_text());s=json.loads((b/'store_packing.json').read_text());fig,ax=plt.subplots(figsize=(8,12));W,H=d['outline_um'];ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=1.5));cmap=plt.get_cmap('tab20')
for c in d['proposed_macros']:
 x,y=c['origin_um'];w,h=c['outline_um'];store='.g_store[' in c['inst'];col=cmap(int(c['inst'].split('.g_store[')[1].split(']')[0])) if store else '#999';ax.add_patch(Rectangle((x,y),w,h,facecolor=col,edgecolor='black',lw=.3))
for w,z in s['per_word_read_source_radius'].items():
 x,y=z['proposed_origin_geometry']['center_um'];x+=10.8+15.996;y+=d['store_base_um'][1]+8.652;ax.scatter([x],[y],marker='x',color='red',s=35);ax.annotate(w,(x,y),fontsize=7)
ax.text(530,1000,'144 store SRAMs\n4×4 banks\n3×3 words/bank\n\nNine read-mux\nword centers (red)\nsource radius348.084um\nFFs NOT placed',fontsize=9,va='center')
ax.text(390,735,'32 native KVQ SRAMs below; source/relay logic placement NOT RUN',fontsize=8,ha='center')
ax.set(xlim=(-20,800),ylim=(-20,H+20),xlabel='um',ylabel='um',title='DISABLED whole-KV-bridge cut PREP\n777.6×1209.6um,176 native SRAMs,no macro overlap\nMacro area506,067.8um² (53.8%); soft-cell size/fill UNMEASURED\n707 functional boundary bits +clock/reset; zero added RTL cycles\nParent FT/clock/reset site NOT selected; no physical release');ax.set_aspect('equal');fig.tight_layout();fig.savefig(b/'whole_kv_bridge_candidate.png',dpi=150)
