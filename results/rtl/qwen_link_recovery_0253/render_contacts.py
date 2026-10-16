import json,pathlib,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=pathlib.Path(__file__).resolve().parents[3];out=root/'results/rtl/qwen_link_recovery_0253'
for name in ['qfd_xs_leaf_m6_138','qfd_xhead_e_m6_138','qfd_xhead_w_m6_138']:
 d=json.load(open(root/'physical/ref_tile'/name/'contact_request.json'));w,h=d['outline']['w'],d['outline']['h'];fig,axs=plt.subplots(1,3,figsize=(13,9),gridspec_kw={'width_ratios':[1.7,1,1]});ax=axs[0]
 ax.add_patch(Rectangle((0,0),w,h,fill=False,color='black'));counts=collections.Counter();colors={'M3':'#008080','M4':'#537acf','M5':'#ad5e00','M6':'#b51f3b'}
 for n,p in d['ports'].items():
  f,c,L=p['face'],p['center_um'],p['layer'];x,y=(0,c)if f=='W'else(w,c)if f=='E'else(c,0)if f=='S'else(c,h);counts[(f,L)]+=1
  ax.plot(x,y,'_',color=colors[L],ms=4);za=axs[1]if f in 'NS'else axs[2];za.plot(c,0 if f in 'SW'else 1,'|',color=colors[L],ms=10,alpha=.6)
 ax.set_aspect('equal');ax.set_xlim(-8,w+8);ax.set_ylim(-5,h+5);ax.set_xlabel('x (um)');ax.set_ylabel('y (um)');ax.set_title(f'{w} x {h} um\nR0 source candidate only')
 axs[1].set_title('N/S exact contact centres');axs[1].set_xlim(0,w);axs[1].set_ylim(-.2,1.2);axs[1].set_yticks([0,1],['S','N']);axs[1].set_xlabel('x (um)')
 axs[2].set_title('W/E exact contact centres');axs[2].set_xlim(0,h);axs[2].set_ylim(-.2,1.2);axs[2].set_yticks([0,1],['W','E']);axs[2].set_xlabel('y (um)')
 text='; '.join(f'{f}/{l}: {n}'for(f,l),n in sorted(counts.items()));fig.suptitle(name+'\n'+text+'\nM5 interior/PG. M6 contacts requested; actual exported pin sizes and parent M7/M9 grants pending.',fontsize=10);fig.tight_layout(rect=[0,0,.99,.9]);fig.savefig(out/(name+'_contacts.png'),dpi=150);plt.close(fig)
