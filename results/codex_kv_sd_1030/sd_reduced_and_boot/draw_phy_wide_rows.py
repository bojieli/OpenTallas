from pathlib import Path
import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).resolve().parent;p=json.load(open(r/'phy_wide_data_ff_rows.json'))
fig,ax=plt.subplots(figsize=(11,13))
ax.add_patch(Rectangle((1860,54),6.24,972,facecolor='lightgrey',edgecolor='black'))
ax.add_patch(Rectangle((1866.24,54),4.32,972,facecolor='wheat',edgecolor='brown'))
ax.add_patch(Rectangle((1877.04,149.904),19.44,179.28,facecolor='lightgreen',alpha=.35,edgecolor='green'))
for c in p['positions'].values():
 x,y=c['xy_um'];w,h=c['body_um'];ax.add_patch(Rectangle((x,y),w,h,facecolor=('royalblue' if c['group']=='TX' else 'purple'),alpha=.65,linewidth=0))
ax.plot([1872.72]*2,[17.28,900],color='orange',lw=1,label='Control/reset spine (reserved boxes not all drawn)')
ax.plot([1874.88]*2,[160,640],'k*',ms=15,label='Primary E clock taps (new clk_t5/6)')
ax.plot([1866.24]*2,[175.944,250.968],color='royalblue',lw=6,label='Actual PHY TX pin span')
ax.plot([1866.24]*2,[603.168,678.336],color='purple',lw=6,label='Actual PHY RX pin span')
ax.text(1883,230,'FDI 2721-FF band\nactual packing pending',ha='center',va='center',fontsize=9,color='darkgreen')
ax.text(1898,105,'TX first240 bits',rotation=90,fontsize=9,va='center')
ax.text(1898,367,'TX last282 bits',rotation=90,fontsize=9,va='center')
ax.text(1898,642,'RX522 bits',rotation=90,fontsize=9,va='center')
ax.set_xlim(1860,1901);ax.set_ylim(0,1040);ax.grid(alpha=.2)
ax.set_xlabel('Type x / um (enlarged)');ax.set_ylabel('Type y / um')
ax.set_title('SD25.92um E-strip actual-master DATA FF row proposal\nTX4698 + RX4698 FFs: pairwise0 overlaps, exact .054/.27 row lattice\nPROPOSAL ONLY: other logic/control/clock/PG legality + electrical model + actual G1 pending')
ax.legend(loc='upper right',fontsize=8);fig.tight_layout();fig.savefig(r/'phy_wide_data_ff_rows.png',dpi=150)
