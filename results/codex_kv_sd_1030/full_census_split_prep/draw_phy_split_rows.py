from pathlib import Path
import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
r=Path(__file__).resolve().parent;d=json.load(open(r/'phy_split_data_ff_rows.json'));p=json.load(open(r/'plan_of_record/plan_c_sd_pg_anchor_v2.json'))
fig,axs=plt.subplots(1,3,figsize=(19,9),gridspec_kw={'width_ratios':[1.4,1,.8]})
colors={'RXwhole':'#1f77b4','TXcapture_PHY':'#d62728','TXmem_S4':'#ff7f0e','TXmem_E5':'#2ca02c','TXmem_E6':'#9467bd'}
for ax in axs:
 ax.add_patch(Rectangle((17.28,54),1848.96,972,color='#ddd'))
 ax.add_patch(Rectangle((1866.24,54),4.32,972,color='#ffcc99'))
 for g,col in colors.items():
  patches=[]
  for n,x in d['positions'].items():
   if x['group']==g:patches.append(Rectangle(x['xy_um'],*x['body_um']))
  ax.add_collection(PatchCollection(patches,facecolor=col,edgecolor='none',label=g))
 for t in p['partition_types']['kv3_sys_SD']['clock']['taps']:ax.plot(*t['xy'],'k*',ms=9)
 for y in [860.085,860.625,868.725,868.96]:ax.plot(1894.8,y,'rx',ms=5)
 ax.grid(alpha=.2);ax.set_xlabel('x / um');ax.set_ylabel('y / um')
axs[0].set(xlim=(0,1900.8),ylim=(0,1036.8),title='Same pins / 7 roots / cycles: DATA FF proposal');axs[0].set_aspect('equal')
axs[1].set(xlim=(1700,1900.8),ylim=(0,65),title='South TX-memory bank (y enlarged)')
axs[2].set(xlim=(1864,1900.8),ylim=(0,920),title='East RX/TX / memory banks (x enlarged)')
fig.suptitle('UNQUALIFIED PREP: 10,440 actual mapped data FFs, no DATA overlaps; full logic / PG / electrical G1 still open\nRed X: 4 existing TX-up/FSTART FFs beyond 220um root reach; physical anchors unresolved')
fig.tight_layout();fig.savefig(r/'phy_split_data_ff_rows.png',dpi=150)
