#!/usr/bin/env python3
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
import numpy as np

r=Path(sys.argv[1])
a=[x.split('\t') for x in (r/'placed_inst.tsv').read_text().splitlines()]
p=[x.split('\t') for x in (r/'placed_pin.tsv').read_text().splitlines()]
fig,axs=plt.subplots(1,2,figsize=(12,8))
for ff,c,size in [(False,'#51718a',.5),(True,'#db8526',1)]:
 q=[x for x in a if x[1].startswith('DFF')==ff]
 axs[0].scatter([(float(x[2])+float(x[4]))/2 for x in q],[(float(x[3])+float(x[5]))/2 for x in q],s=size,c=c,alpha=.45,label='FF' if ff else 'logic')
axs[0].scatter([float(x[2]) for x in p],[float(x[3]) for x in p],s=3,c='red',label='pins')
axs[0].legend()
# Actual rectangle/bin intersections measure density, rather than cell centres.
d=np.zeros((15,12)); dx=115.344/12;dy=140.4/15
for z in a:
 x0,y0,x1,y1=map(float,z[2:6])
 for j in range(max(0,int(y0/dy)),min(15,int(y1/dy)+1)):
  for i in range(max(0,int(x0/dx)),min(12,int(x1/dx)+1)):
   d[j,i]+=max(0,min(x1,(i+1)*dx)-max(x0,i*dx))*max(0,min(y1,(j+1)*dy)-max(y0,j*dy))/(dx*dy)
im=axs[1].imshow(d,origin='lower',extent=(0,115.344,0,140.4),vmin=0,vmax=1,cmap='YlOrRd',aspect='equal')
fig.colorbar(im,ax=axs[1],label='rectangle area / bin area')
for ax in axs:
 ax.set_xlim(0,115.344);ax.set_ylim(0,140.4);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um')
axs[0].set_title('Actual fresh raw-fault LSL placement\nHA/FA expansion; 12,030 retained FF; 0 added cycles')
axs[1].set_title(f'Density: peak {d.max():.3f}')
fig.tight_layout();fig.savefig(r/'place.png',dpi=150)
print('cells',len(a),'FF',sum(x[1].startswith('DFF') for x in a),'peak_bin',float(d.max()))
