import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
import json,sys,re
p=Path(sys.argv[1]);fig,axs=plt.subplots(1,2,figsize=(16,9))
for ax,tag in zip(axs,['A_pin_bundles','B_tall_banks']):
 td=p/tag;f=json.load(open(td/'positions.json'));pins=json.load(open(td/'phy_pins.json'))
 ax.add_patch(Rectangle((40.04,0),727.328,1113.64,fc='#f4d6a3',ec='brown',alpha=.4,label='full PHY PG envelope'))
 ax.add_patch(Rectangle((103.68,0),600.048,1050,fill=False,ec='black',lw=1.2))
 ax.add_patch(Rectangle((181.44,1088.64),241.92,397.44,fc='#c9d6eb',ec='navy',alpha=.6,label='EP macro'))
 for pr,col in [('rx_s0','red'),('rx_s1','orange'),('rx_s2','green'),('rx_s3','purple'),('tx_s0','pink'),('tx_s1','cyan'),('tx_s2','blue'),('tx_s3','darkred')]:
  a=[v for n,v in f.items() if n.startswith(pr+'_')];ax.scatter([x for x,y in a],[y for x,y in a],s=2,c=col,label=pr)
 for pr,col in [('rx','red'),('tx','navy')]:
  a=[v for n,v in pins.items() if n.startswith(pr+'[')];ax.scatter([x for x,y in a],[y for x,y in a],s=3,c=col,marker='x')
 for b in range(0,512,32):
  pts=[pins[f'rx[{b}]'],f[f'rx_s0_b{b}']];ax.plot([v[0] for v in pts],[v[1] for v in pts],c='red',lw=.25,alpha=.6)
  pts=[f[f'tx_s3_b{b}'],pins[f'tx[{b}]']];ax.plot([v[0] for v in pts],[v[1] for v in pts],c='navy',lw=.25,alpha=.6)
 ax.set_xlim(-20,850);ax.set_ylim(430,1145);ax.set_aspect('equal');ax.set_title(tag+'\nmodeled M6/M7 escape, same 4104 FF and 5130 nets');ax.set_xlabel('um');ax.set_ylabel('um')
axs[1].legend(loc='upper right',fontsize=7);fig.tight_layout();fig.savefig(sys.argv[2],dpi=140)
