"""121b plot.py method, expanded to every actual native box/row/pin and area bins."""
import hashlib,json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
import numpy as np
from dft.liberty import read_liberty
p,libs,q=map(Path,sys.argv[1:]);j=json.loads((p/'native/positions.json').read_text());pre=json.loads((p/'pre_native/positions.json').read_text());raw=json.loads((p/'native/raw.json').read_text());native=read_liberty(sorted(libs.glob('*_TT_*.lib*')));u=j['units'];die=[v/u for v in j['die']];x0,y0,x1,y1=die
ident=json.loads((q/'checkpoint_identity.json').read_text()); kinds={r['instance']:r['kind'] for r in ident['rows']}; fig,ax=plt.subplots(figsize=(12,7));boxes=[];colors=[];centers=[]
for r in j['rows']:
 x,y,X,Y=[v/u for v in r];ax.add_patch(Rectangle((x,y),X-x,Y-y,facecolor='#eeeeee',edgecolor='none',zorder=0))
# Density is sum of actual intersected cell area / actual bin area, no smoothing.
nx=int(np.ceil((x1-x0)/5));ny=int(np.ceil((y1-y0)/5));xe=np.linspace(x0,x1,nx+1);ye=np.linspace(y0,y1,ny+1);occupied=np.zeros((ny,nx))
for name,c in j['insts'].items():
 x,y,X,Y=[v/u for v in c['bbox']];boxes.append(Rectangle((x,y),X-x,Y-y));lib=native.get(c['master'],{});ff=bool(lib.get('ff'))
 constant=any(str(q.get('function')) in ('0','1') for q in lib.get('pins',{}).values())
 colors.append(('#d62728' if kinds[name]=='TREE' else '#00bfc4') if name not in pre['insts'] else '#843c39' if constant else '#ffae42' if ff else '#167baa')
 if ff:centers.append(((x+X)/2,(y+Y)/2))
 occupied+=np.maximum(0,np.minimum(ye[1:],Y)-np.maximum(ye[:-1],y))[:,None]*np.maximum(0,np.minimum(xe[1:],X)-np.maximum(xe[:-1],x))[None,:]
ax.add_collection(PatchCollection(boxes,facecolors=colors,linewidths=0))
for name,ps in j['bterms'].items():
 for pin in ps:
  for layer,x,y,X,Y in pin['boxes']:
   ax.plot([(x+X)/(2*u)],[(y+Y)/(2*u)],'.',color='magenta' if name=='clk' else '#222222',markersize=5 if name=='clk' else 1)
cx=sum(x for x,y in centers)/len(centers);cy=sum(y for x,y in centers)/len(centers);ax.plot([cx],[cy],'+',color='black',markersize=12,label='FF centroid')
ax.set_xlim(x0,x1);ax.set_ylim(y0,y1);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um');ax.set_title('CHECKPOINT / UNQUALIFIED / IDENTITY PENDING REVIEW\nred=TREE; cyan=open LOAD; brown=ties; orange=FF; magenta=clock entry');ax.legend();fig.tight_layout();fig.savefig(q/'checkpoint_floorplan.png',dpi=180);plt.close(fig)
density=occupied/(np.diff(ye)[:,None]*np.diff(xe)[None,:]);fig,ax=plt.subplots(figsize=(12,7));im=ax.pcolormesh(xe,ye,density,vmin=0,vmax=max(1,float(density.max())),cmap='viridis');fig.colorbar(im,ax=ax,label='sum native cell intersection area / bin area');ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um');ax.set_title('CHECKPOINT / UNQUALIFIED / IDENTITY PENDING REVIEW\nNative occupancy; <=5 um bins; no smoothing or routed density');fig.tight_layout();fig.savefig(q/'checkpoint_density.png',dpi=180)
(q/'render_geometry.json').write_text(json.dumps({'scope':'checkpoint/unqualified/identity pending ROOT review; actual exported cell boxes only','bin_count':[nx,ny],'FF_centroid_um':[cx,cy],'cell_count':len(j['insts']),'native_density_max':float(density.max())},indent=2)+'\n')
