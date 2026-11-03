from pathlib import Path
import json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent;E=json.load(open('/home/ubuntu/coord/tmp/codex-bfqg-cut-export-0315/collected/guide_pins.json'));J=json.load(open(P/'native_join.json'));fig,axs=plt.subplots(1,2,figsize=(13,9));colors={'M1':'#bcbcbc','M2':'#278f3d','M3':'#1668b2','M4':'#bb58a1','M5':'#d98300'}
for ax,name in zip(axs,['_00113_','_00118_']):
 n=next(n for n in E['nets']if n['name']==name);r=next(r for r in J['rows']if r['name']==name)
 for m in E['macros']:
  x,y,xx,yy=m['box_um']
  if x>125 or y>180:continue
  ax.add_patch(Rectangle((x,y),xx-x,yy-y,color='.86'));ax.text(x+5,y+15,m['instance'],fontsize=9)
 for q in n['guides']:
  x,y,xx,yy=q['box_um'];ax.add_patch(Rectangle((x,y),xx-x,yy-y,facecolor=colors[q['layer']],edgecolor='none',alpha=.75))
 x,y,xx,yy=r['proxy_box'];ax.add_patch(Rectangle((x,y),xx-x,yy-y,facecolor='none',edgecolor='red',linestyle='--',linewidth=1.4,label='endpoint proxy bbox'))
 ax.axhline(107.5,color='black',linestyle=':',lw=1);ax.plot([10,17],[107.5,107.5],color='red',lw=5,label='raw hot cut x10..17')
 for t in n['terms']:
  x,y=t['proxy_cell_centre_um'];ax.scatter([x],[y],s=25,color='black',zorder=10)
 ax.set(xlim=(0,125),ylim=(0,180),aspect='equal',xlabel='um',ylabel='um',title=name+' actual saved native guide corridors')
 ax.legend(loc='lower right',fontsize=8)
fig.suptitle('BFQG local proxy1.04: actual guides escape endpoint bbox\nleft: M3 crosses central street x114.57..115.14; right: M5 crosses west x5.70..6.27\nGuides are not detailed wires/DRC; raw FAIL/9registration/CTS holds remain',fontsize=11);fig.tight_layout(rect=(0,0,1,.92));fig.savefig(P/'actual_native_cut_examples.png',dpi=160)
