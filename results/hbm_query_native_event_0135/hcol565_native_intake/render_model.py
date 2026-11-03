from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).resolve().parent
fig,axes=plt.subplots(1,2,figsize=(13,7))
for h,ax in enumerate(axes):
 pins=json.loads((p/f'model/pins_h{h}.json').read_text());W,H=218.592,225.504
 ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=2))
 for r,xc in [(0,8.64),(1,118.8)]:
  ax.add_patch(Rectangle((xc,20),90,185,fill=False,ls='--',edgecolor='#8493a5'))
  ax.text(xc+45,153,f'Region {r}\n565 query + 544 key\nown existing captures\n2 local heads',ha='center',va='center',fontsize=9)
 ax.text(W/2,24,'Dashed boxes: reference affinity only\nNo guides or placed cells generated',ha='center',fontsize=8)
 for face,color in [('W','#2f7ea7'),('E','#2f7ea7'),('N','#b65d2e'),('S','#b65d2e')]:
  q=[v for v in pins if v['face']==face];ax.scatter([v['x']for v in q],[v['y']for v in q],s=3,c=color)
 c=[v for v in pins if v['bus']=='clk_pair'];ax.scatter([v['x']for v in c],[v['y']for v in c],s=65,marker='*',c='red',zorder=4)
 ax.text(112.32,106,'2 clock ports\nreference entry',ha='center',va='top',fontsize=8,color='red')
 ax.text(-4,H/2,'1127 native pins @0.192um',rotation=90,ha='right',va='center',fontsize=8)
 ax.text(W+4,H/2,'1127 native pins @0.192um',rotation=90,ha='left',va='center',fontsize=8)
 ax.set(xlim=(-20,W+20),ylim=(-12,H+12),aspect='equal',xlabel='um',ylabel='um',title=f'HCOL565 h{h}: {len(pins)} true ABI bits\n{26329 if h==0 else 29164} declared state bits / 0 SRAM')
fig.suptitle('Disabled exact SOURCE13 regional/head5 component intake model\nDELIVERED_RESET1 / selected DRST0 / one reset copy per region / +0 cycles\nNo native GEN, placement, clock/parent adoption or all-pair reach credit',fontsize=11)
fig.tight_layout();fig.savefig(p/'hcol565_source_model.png',dpi=145)
