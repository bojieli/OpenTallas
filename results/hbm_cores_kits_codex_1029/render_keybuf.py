import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).resolve().parent
mp=json.load(open(p/'keybuf_macro_placement.json'))
f,a=plt.subplots(1,2,figsize=(9,6))
for ax,title,root in zip(a,['Inherited centre root: FAIL','Five SRAMs + E-channel root: PREP'],[(120.936,146.88),(207.384,146.88)]):
 ax.add_patch(Rectangle((0,0),241.92,293.76,fill=False,color='black'))
 for k,m in enumerate(mp['macro_placement']):
  x,y=m['origin_um'];ax.add_patch(Rectangle((x,y),172.8,41.04,facecolor='lightgray',edgecolor='black'));ax.text(x+86.4,y+20.5,f'gm[{k}]',ha='center',fontsize=8)
 x,y=root;ax.add_patch(Rectangle((x-4.32,y-4.32),8.64,8.64,color='red',alpha=.7));ax.plot(x,y,'r*');ax.set_xlim(-5,248);ax.set_ylim(-5,301);ax.set_aspect('equal');ax.set_title(title,fontsize=10);ax.set_xlabel('um')
f.tight_layout();f.savefig(p/'keybuf_entry_review.png',dpi=140)
