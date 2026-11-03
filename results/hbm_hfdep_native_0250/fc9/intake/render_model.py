from pathlib import Path
import json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).parent;m=json.loads((r/'model.json').read_text());pins=json.loads((r/'pins.json').read_text());w,h=m['outline_reference_um'];fig,ax=plt.subplots(figsize=(12,8));ax.add_patch(Rectangle((0,0),w,h,fill=False,lw=2))
for q in m['macros']:
 x,y,a,b=q['x'],q['y'],q['w'],q['h'];ax.add_patch(Rectangle((x-4.32,y-4.32),a+8.64,b+8.64,fill=False,ls='--',ec='gray'));ax.add_patch(Rectangle((x,y),a,b,fc='#c9dbe6',ec='#456'));ax.text(x+a/2,y+b/2,q['instance'].replace('\\','').replace('u_rxb.',''),ha='center',va='center',fontsize=8)
for bus,c in [('tx_frame','#d37e38'),('sd_rx','#3995ad'),('sd_tx','#9d55a6'),('rx_pin_flit','#387b4a'),('fault_cause','#333')]:
 ps=[p for p in pins if p['bus']==bus];ax.scatter([p['x']for p in ps],[p['y']for p in ps],s=4,color=c,label=f'{bus}: {len(ps)}')
clk=next(p for p in pins if p['bus']=='clk');ax.scatter(clk['x'],clk['y'],marker='*',s=130,c='red');ax.annotate('reference clk220.344,25.92\nparent clock/reset join HELD',(clk['x'],clk['y']),(245,5),arrowprops={'arrowstyle':'->'},fontsize=9)
ax.set(xlim=(-8,w+8),ylim=(-15,h+15),aspect='equal',xlabel='um',ylabel='um',title='Additive HF FC9 source/ABI PREP: 2286bits =1148in+1138out\nFour true64×512 SRAMs; same calendar/reset/clock/pipeline; no outside FF shell')
ax.legend(loc='upper center',bbox_to_anchor=(.5,-.08),ncol=5,fontsize=8);fig.text(.5,.015,'Reference geometry only; no native FC9GEN/SYNTH/P&R or physical timing credit.\nSelected2288/native4two-bit failure preserved; four paired carriers/rootOBS136 event remains disabled.',ha='center',fontsize=10);fig.tight_layout(rect=[0,.08,1,1]);fig.savefig(r/'fc9_source_model.png',dpi=140)
