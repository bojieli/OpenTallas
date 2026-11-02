import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
b=Path(__file__).parent;p=json.loads((b/'store_packing.json').read_text());t=json.loads((b/'macro_inventory.json').read_text())
fig,axs=plt.subplots(1,2,figsize=(14,8),gridspec_kw={'width_ratios':[1.4,1]});cmap=plt.get_cmap('tab20')
for ax,key in zip(axs,['old','proposed']):
 for s in p['store_macros']:
  x,y=s[key];w,h=s['size'];ax.add_patch(Rectangle((x,y),w,h,facecolor=cmap(s['bank']),edgecolor='black',lw=.3))
 if key=='old':
  for m in t['contents']:
   if '.u_bank.g_kvq[' in m['inst']:
    x,y=m['origin_um'];w,h=m['outline_um'];ax.add_patch(Rectangle((x,y),w,h,facecolor='#aaa',edgecolor='black',lw=.3,alpha=.6))
  ax.set(xlim=(1635,2860),ylim=(0,1226.88),title='CURRENT: gray=32 KVQ SRAMs, color=144 store SRAMs\nStore word minimum read-source radius:570.24–643.476 um (FAIL405)')
 else:
  for w,z in p['per_word_read_source_radius'].items():
   x,y=z['proposed_origin_geometry']['center_um'];ax.scatter([x+15.996],[y+8.652],marker='x',s=50,color='red');ax.annotate(w,(x+15.996,y+8.652),fontsize=7)
  ax.set(xlim=(-15,520),ylim=(-15,420),title='PROPOSED STORE ONLY:4×4 banks ×3×3 words\n502.704×397.464 um; per-word radius348.084 um\nRed crosses: origin-center +macro center, not placed FFs')
 ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um')
fig.suptitle('S81 kv_leaf__t2 source-cut/geometry census — no CAD, no canonical edits\nSame144 SRAMs, same42.792×34.56 pitches, unchanged native drain calendar; full cut/clock/FT qualification remains open',fontsize=12)
fig.tight_layout(rect=(0,0,1,.92));fig.savefig(b/'store_repack_census.png',dpi=150)
