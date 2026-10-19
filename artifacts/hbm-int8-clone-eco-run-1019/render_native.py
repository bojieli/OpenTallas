"""Native geometry diagnostic only; no routed or closure claim."""
import json,sys,hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
import numpy as np
p=Path(sys.argv[1]);a=json.loads(Path(sys.argv[2]).read_text());j=json.loads((p/'native/positions.json').read_text());u=j['units'];x0,y0,x1,y1=[v/u for v in j['die']]
fig,ax=plt.subplots(figsize=(12,7));boxes=[];colors=[];centers=[]
for r in j['rows']:
 x,y,X,Y=[v/u for v in r];ax.add_patch(Rectangle((x,y),X-x,Y-y,facecolor='#eeeeee',edgecolor='none'))
nx=int(np.ceil((x1-x0)/5));ny=int(np.ceil((y1-y0)/5));xe=np.linspace(x0,x1,nx+1);ye=np.linspace(y0,y1,ny+1);occ=np.zeros((ny,nx))
for n,c in j['insts'].items():
 x,y,X,Y=[v/u for v in c['bbox']];boxes.append(Rectangle((x,y),X-x,Y-y));ff='DFF' in c['master'];colors.append('#d62728' if n in a['added_cells'] else '#9457eb' if n in a['replacement_cells'] else '#ffae42' if ff else '#167baa')
 if ff:centers.append(((x+X)/2,(y+Y)/2))
 occ+=np.maximum(0,np.minimum(ye[1:],Y)-np.maximum(ye[:-1],y))[:,None]*np.maximum(0,np.minimum(xe[1:],X)-np.maximum(xe[:-1],x))[None,:]
ax.add_collection(PatchCollection(boxes,facecolors=colors,linewidths=0))
for n,ps in j['bterms'].items():
 for pin in ps:
  for layer,x,y,X,Y in pin['boxes']:ax.plot([(x+X)/(2*u)],[(y+Y)/(2*u)],'.',color='magenta' if n=='clk' else '#222',markersize=5 if n=='clk' else 1)
centroid=[sum(c[k] for c in centers)/len(centers) for k in range(2)];ax.plot(*centroid,'k+',markersize=12,label='FF centroid');ax.legend();ax.set(xlim=(x0,x1),ylim=(y0,y1),xlabel='um',ylabel='um',title='INT8 native exact clone: red=added; purple=replaced; orange=FF; magenta=clock port');ax.set_aspect('equal');fig.tight_layout();fig.savefig(p/'eco_floorplan.png',dpi=180);plt.close(fig)
dens=occ/(np.diff(ye)[:,None]*np.diff(xe)[None,:]);fig,ax=plt.subplots(figsize=(12,7));im=ax.pcolormesh(xe,ye,dens,vmin=0,vmax=max(1,float(dens.max())),cmap='viridis');fig.colorbar(im,ax=ax,label='actual cell intersection area / bin area');ax.set_aspect('equal');ax.set(xlabel='um',ylabel='um',title='INT8 exact clone native cell occupancy; <=5 um bins; no routing claim');fig.tight_layout();fig.savefig(p/'eco_density.png',dpi=180)
(p/'render_native.json').write_text(json.dumps(dict(cells=len(j['insts']),rows=len(j['rows']),FFvisual_count=len(centers),FF_centroid_um=centroid,density_max=float(dens.max()),bin_count=[nx,ny],source_geometry_sha256=hashlib.sha256((p/'native/positions.json').read_bytes()).hexdigest(),diagnostic_only=True),indent=2)+'\n')
