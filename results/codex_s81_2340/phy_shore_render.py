import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
j=json.load(open(sys.argv[1]));w,h=j['outline_um'];fig,axes=plt.subplots(2,1,figsize=(14,13))
a=axes[0];a.add_patch(Rectangle((63.64,302.4),2608.48,924.48,fc='grey',alpha=.3,label='actual current typed PHY'))
a.axhline(96.32,ls='--',c='red',label='shoreline200um maximum PHY origin')
a.set_title('Current actual ES0/ES1 typed placement: PHY begins406.08um from die edge; old IO metadata hides it')
b=axes[1];m=j['macro_um'];d=j['domain_um'];b.add_patch(Rectangle((d[0],d[1]),d[2]-d[0],d[3]-d[1],fc='cyan',alpha=.15,label='PHY PG domain, same63.64um guard'))
b.add_patch(Rectangle((m[0],m[1]),m[2]-m[0],m[3]-m[1],fc='grey',alpha=.4,label='same2608.48x924.48 PHY footprint'))
for s,c in zip(j['slots'],['purple','orange']):
 p=s['centreline_um'];b.plot(*zip(*p),c=c,lw=2,label=s['name']+f" stations{s['stations']} max{s['all_bit_max_hop_um']:.3f}um")
 for x0,y0,x1,y1 in s['bank_rects_um']:b.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,ec=c,fc=c,alpha=.6))
b.axhline(96.32,ls='--',c='red');b.set_title('Feasibility candidate only: shoreline199.72um, sameguard/outline; FT0+5cycles, FT1unchanged; no build')
for ax in axes:
 ax.set_xlim(-20,w+20);ax.set_ylim(-103.68,h+20);ax.set_aspect('equal');ax.axhline(-103.68,c='black');ax.set_xlabel('typex um');ax.set_ylabel('typey um');ax.legend(fontsize=8,loc='center')
fig.tight_layout();fig.savefig(sys.argv[2],dpi=140)
