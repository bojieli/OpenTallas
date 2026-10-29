import sys,json,copy
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0,'tools/die_plan')
import clock_landing_plan as C
p=json.load(open(sys.argv[1]));folder=Path(sys.argv[2]);out=Path(sys.argv[3]);names=['svc_hi_dsdv_svc_rs__t3','svc_hi_dsdv_svc_rs__t5']
fig,axes=plt.subplots(1,2,figsize=(13,12))
for ax,n in zip(axes,names):
 t=p['partition_types'][n];result=json.load(open(folder/(n+'.json')));r=min(result['candidates'],key=lambda r:(r['bands_failed'],sum(abs(x) for x in r['translation_um'])))
 dx,dy=r['translation_um'];w,h=t['outline_um']
 for c in t.get('hard_cores',[]):
  x,y=c['origin_um'];a,b=c['outline_um'];ax.add_patch(Rectangle((x+dx,y+dy),a,b,fc='grey',alpha=.4))
 for f in t.get('ft_slots',[]):
  for st in f.get('bit_sites_um',[]):
   cw,ch=f['bit_site_cell_um'];xs=[q[0]+dx for q in st];ys=[q[1]+dy for q in st]
   ax.add_patch(Rectangle((min(xs),min(ys)),max(xs)-min(xs)+cw,max(ys)-min(ys)+ch,fc='orange',alpha=.8))
 for bus,b in r['bands'].items():
  x0,y0,x1,y1=b['rect_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='blue',alpha=.3));ax.text(x0,y0,bus,fontsize=5)
 for f in r['failures']:
  x,y=C._bus_xy(t,f['bus']);ax.scatter([x],[y],c='red',s=60);ax.text(x+12,y,f['bus'],color='red',fontsize=8)
 ax.set_xlim(-50,w+20);ax.set_ylim(-20,h+20);ax.set_aspect('equal');ax.set_title(f'{n}\nshift {dx},{dy}; {r["bands_failed"]} blocked bands');ax.set_xlabel('um');ax.set_ylabel('um')
fig.tight_layout();fig.savefig(out,dpi=160)
