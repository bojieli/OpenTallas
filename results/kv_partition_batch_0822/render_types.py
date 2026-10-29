import json,sys
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/die_plan'));import schema as S,gen_phys as G
P=S.Plan(S.load(sys.argv[1]),sys.argv[1]);names=['kv3_hroot','kv3_io_cor','kv3_io_cor_v1','kv3_io_ft','kv3_io_ft_v1','kv3_hub_Ei','kv3_sys_SD','kv3_sys_SD_v1','kv3_sys_c']
fig,axes=plt.subplots(3,3,figsize=(15,15))
for tn,ax in zip(names,axes.flat):
 t=P.types[tn];w,h=t['outline_um'];ax.add_patch(Rectangle((0,0),w,h,fill=False))
 for x0,y0,x1,y1 in t.get('clock',{}).get('die_islands_um',[]):ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,color='#55aa66',alpha=.45))
 for c in t.get('contents',[])+t.get('hard_cores',[]):
  if 'origin_um' not in c or 'outline_um' not in c:continue
  x,y=c['origin_um'];a,b=c['outline_um'];ax.add_patch(Rectangle((x,y),a,b,facecolor='#aaaaaa',edgecolor='black',alpha=.5))
 for sl in t.get('ft_slots',[]):
  q=sl.get('regs_um',[])
  if q:
   ax.plot([x[0] for x in q],[x[1] for x in q],color='#2266aa',lw=.5,alpha=.4);ax.scatter([x[0] for x in q],[x[1] for x in q],color='#2266aa',s=2)
 pins=G.type_pins(P,tn)
 if pins:ax.scatter([p[3] for p in pins],[p[4] for p in pins],s=.25,color='#662266')
 ck=t.get('clock',{}).get('tap_um');rs=t.get('reset',{}).get('tap_um')
 if ck:ax.scatter([ck[0]],[ck[1]],marker='*',c='orange',s=55)
 if rs:ax.scatter([rs[0]],[rs[1]],marker='s',c='red',s=15)
 ax.set_aspect('equal');ax.set_xlim(-.02*w,1.02*w);ax.set_ylim(-.02*h,1.02*h);ax.set_title(tn+' '+str(t['outline_um'])+'\n'+str(len(t.get('ft_slots',[])))+' FT / '+str(len(t.get('clock',{}).get('die_islands_um',[])))+' native body reserves',fontsize=9)
fig.suptitle('Current KV event27f strict bound / exact actual clock+provider union / pre-place geometry\ngreen=top-owned body/PG cut; blue=planned FT chain; purple=bus pins; orange=clockentry; red=resetentry')
fig.tight_layout();fig.savefig(sys.argv[2],dpi=140)
