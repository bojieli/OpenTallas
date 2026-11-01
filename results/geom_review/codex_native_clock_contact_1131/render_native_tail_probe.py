from pathlib import Path
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).resolve().parent
m=json.loads((r/'native_tail_pin_narrow/manifest.json').read_text())
fig,axes=plt.subplots(1,2,figsize=(12,6),gridspec_kw={'width_ratios':[1.2,1]})
for ax in axes:
    x,y=m['native_origin_um'];w,h=m['native_size_um']
    ax.add_patch(Rectangle((x,y),w,h,color='salmon',alpha=.35))
    for core in m['other_core_obstacles']:
        a,b,c,d=core['box'];ax.add_patch(Rectangle((a,b),c-a,d-b,color='grey',alpha=.35))
    for index in range(math.ceil(5480/4.32),math.floor(5740/4.32)+1):
        ax.axhline(index*4.32,color='grey',alpha=.2,lw=1)
    for index in range(math.ceil(920/4.32),math.floor(1200/4.32)+1):
        ax.axvline(index*4.32,color='grey',alpha=.2,lw=1)
    sx,sy=m['source_xy_um']
    ax.add_patch(Rectangle((sx,sy),1.62,.27,color='black'))
    x,y=m['clock_xy_um']
    ax.add_patch(Rectangle((x-.024,y-.24),.048,.48,color='green'))
    a,b,c,d=m['native_upper_M6_M7_window_um']
    ax.add_patch(Rectangle((a,b),c-a,d-b,fill=False,edgecolor='green',ls='--',lw=1))
    ax.scatter(*m['drive_xy_um'],color='blue',s=20)
    ax.set_aspect('equal');ax.grid(alpha=.1)
axes[0].set_xlim(930,1190);axes[0].set_ylim(5500,5720)
axes[0].text(1065,5703,'actual b5607',fontsize=8)
axes[0].text(970,5535,'actual SIGNED tail1 LEF\ncurrent C11E position\n218.592 × 187.488',fontsize=10)
axes[0].set_title('Actual source → actual native M5 CLK, 99.384 um')
x,y=m['clock_xy_um']
axes[1].set_xlim(x-4,x+4);axes[1].set_ylim(y-4,y+4)
axes[1].annotate('M6/M7 dogleg to M8 PG gap',xy=(x,y+2.16),xytext=(x-3.7,y+3.1),arrowprops={'arrowstyle':'->'},fontsize=8)
axes[1].set_title('Lib clock:true; LEF USE SIGNAL\nOnly M6/M7 clock access opens inside macro')
fig.suptitle('Physical native clock-contact vehicle, .04/.16 NDR variants. No virtual native-clock BTerm.\nSource/functional qualification and current die G4 remain held.',fontsize=10)
fig.tight_layout();fig.savefig(r/'native_tail_pin_review.png',dpi=150)
