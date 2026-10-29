import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent
p=json.loads((P/'programme_store_macro_candidate.json').read_text());e=json.loads((P/'programme_store_estimate.json').read_text());v=json.loads((P/'vp4_estimate.json').read_text())
f,ax=plt.subplots(1,2,figsize=(15,8))
for a,(w,h),title in zip(ax,[p['outline_um'],v['outline_um']],['Programme store: source-local leaf candidate (ESTIMATE)','VP4 conservative channel budget (ESTIMATE)']):
 a.set_xlim(0,w);a.set_ylim(0,h);a.set_aspect('equal');a.set_title(title);a.set_xlabel('um');a.set_ylabel('um')
for z in e['leaf_logic_guides']:
 x,y,xx,yy=z['rect_um'];ax[0].add_patch(Rectangle((x,y),xx-x,yy-y,fill=False,ec='#4178a8',lw=.8));ax[0].text(x+142.56,y+90.72,'L'+str(z['leaf']),ha='center',va='center',fontsize=8)
for m in p['macro_placement']:
 x,y=m['origin_um'];ax[0].add_patch(Rectangle((x,y),96.552,69.66,fc='#9ecae1',ec='#286493',lw=.5))
for m in v['macro_positions']:
 x,y=m['origin_um'];ax[1].add_patch(Rectangle((x,y),94.8,41.1,fc='#b0d6af',ec='#397c36',lw=.5))
for a,xy in [(ax[1],v['clock_entry_um'])]:a.plot(*xy,'r+',ms=13)
f.tight_layout();f.savefig(P/'macro_candidates.png',dpi=150)
