import sys,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=Path(sys.argv[1]);sys.path[:0]=[str(root/'tools'),str(root/'tools/die_plan')]
import schema as S
from die_hop_scan import pin_table,station_site,input_site
p=json.loads(Path(sys.argv[2]).read_text());P=S.Plan(p);t=p['partition_types']['hd_spn_wshim_rx'];s=t['ft_slots'][0];pins=pin_table(P,'hd_spn_wshim_rx')
fig,ax=plt.subplots(figsize=(9,10));w,h=t['outline_um'];ax.add_patch(Rectangle((0,0),w,h,fill=False,color='black'))
for bit in range(0,s['width']+1,20):
 a=pins['link_i'].get(bit);b=pins['link_o'].get(bit)
 if a is None or b is None:continue
 ap=input_site(a);bp=input_site(b)
 pts=[ap]+[station_site(s,i,bit,a,b) for i in range(1,s['stations'])]+[bp]
 ax.plot([q[0] for q in pts],[q[1] for q in pts],'-o',ms=2,lw=.5,color='#4488bb')
b=t['clock']['landing_contract']['bands']['link_i']
for name,key,col in [('FREG','freg_rect_um','#66bb88'),('ring8','rect_um','#eeaa44')]:
 r=b[key];ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fill=False,color=col,lw=2));ax.text(r[0],r[3]+5,name,color=col)
for pin in t['clock']['landing_contract']['pins']:
 x,y=pin['xy_um'];ax.plot(x,y,'r.',ms=4)
ax.set_aspect('equal');ax.set_xlim(-15,w+15);ax.set_ylim(-15,h+45);ax.set_title('Private HEAD RX vC candidate: 6 hops (~117 um), FREG +1; FT +3\nWREG8 / DSREP8, original slot and pin contract; no macros')
fig.savefig(sys.argv[3],dpi=130,bbox_inches='tight')
