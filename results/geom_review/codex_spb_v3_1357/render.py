from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ls=[l.split('\t') for l in Path(__file__).with_name('actual.tsv').read_text().splitlines()]
mac={l[1]:l for l in ls if l[0]=='I' and l[2].endswith('_PROBE')}
ff=[l for l in ls if l[0]=='I' and l[2].startswith('DFF')]
rp=[l for l in ls if l[0]=='P' and l[1]=='phy' and l[2].startswith('rx[')]
phy=mac['phy'];ox,oy=map(float,phy[4:6]);pins=[(float(l[4])+ox,float(l[5])+oy) for l in rp]
fig,ax=plt.subplots(1,2,figsize=(13,7),gridspec_kw={'width_ratios':[1,1.2]})
for a in ax:
 for k,l in mac.items():
  x,y,X,Y=map(float,l[4:8]);a.add_patch(Rectangle((x,y),X-x,Y-y,color='#dddddd',alpha=.6));a.text(x+5,y+20,k)
 a.scatter([(float(l[4])+float(l[6]))/2 for l in ff],[(float(l[5])+float(l[7]))/2 for l in ff],s=2,c='#2766a3',label='actual 4104 FF bodies')
 a.scatter([p[0] for p in pins],[p[1] for p in pins],s=12,c='#d44',label='actual PHY rx M7 pins')
 a.axvline(ox,c='gray',ls='--',lw=.7);a.set_xlabel('um');a.set_ylabel('um');a.grid(alpha=.15)
ax[0].set_xlim(-10,740);ax[0].set_ylim(-10,1510);ax[0].set_title('Actual routed-probe ODB: fixed macros / FFs')
ax[1].set_xlim(-3,160);ax[1].set_ylim(470,665);ax[1].set_title('PHY W escape: 512 rx pins / 3 staggered rows')
ax[1].legend(loc='lower left',fontsize=8)
fig.suptitle('SPB V3_stagger3 — independent native ODB geometry review\nGRT M6 total overflow 0; pin-access macroNoAp 0 (existing run)')
fig.tight_layout();fig.savefig(Path(__file__).with_name('spb_v3_actual.png'),dpi=150)
