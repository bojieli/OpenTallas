import gzip,json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
D=Path(__file__).parent;p=json.load(gzip.open(D/'plan_spine_raw.json.gz','rt'));parts={q['name']:q for q in p['partitions']};ox=8069.76;oy=12925.44
fig,ax=plt.subplots(figsize=(8,11));ax.add_patch(Rectangle((0,0),1382.4,2073.6,fill=False,ls='--',ec='grey'))
for n in ['sp0','sp0_xw_o_shim','sp0_xe_o_shim','sp0_bw_i_shim','sp0_be_i_shim']:
 q=parts[n];t=p['partition_types'][q['type']];x,y=q['origin_um'];x-=ox;y-=oy;w,h=t['outline_um'];ax.add_patch(Rectangle((x,y),w,h,facecolor='#c6d8ef' if n=='sp0' else '#b1ddbb',edgecolor='black'));ax.text(x+w/2,y+h/2,n.replace('sp0_',''),ha='center',rotation=90 if w<150 else 0,fontsize=8)
 if n=='sp0':
  for c in t['contents']:
   a,b=c['origin_um'];cw,ch=c['outline_um'];ax.add_patch(Rectangle((x+a,y+b),cw,ch,facecolor='red'))
  for s in t['internal_stations']:
   xy=s['regs_um'];ax.plot([x+a for a,b in xy],[y+b for a,b in xy],'.',ms=4)
ax.set_xlim(-40,1420);ax.set_ylim(-40,2110);ax.set_aspect('equal');ax.set_title('Final sp0 strip+ribbons; data windows unchanged\nS extension carries reset sites within reach; no added data cycle')
fig.tight_layout();fig.savefig(D/'png/spine_split.png',dpi=110)
