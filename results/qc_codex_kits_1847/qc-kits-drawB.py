import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as p
from matplotlib.patches import Rectangle
rows=[l.rstrip().split('\t') for l in open('/tmp/qc-kits-placement2.tsv')]
fig,ax=p.subplots(figsize=(12,6));xy=[]
for n,m,*v in rows:
 x,y,xx,yy=[int(z)/2000 for z in v[:4]]
 if v[4]=='1':ax.add_patch(Rectangle((x,y),xx-x,yy-y,facecolor='#6d8aaa',alpha=.6))
 elif n in ['_08635_','_08662_','_08702_','_08756_','_15169_']:ax.scatter((x+xx)/2,(y+yy)/2,c='red',s=30)
 elif n.startswith('ot_ms_'):ax.scatter((x+xx)/2,(y+yy)/2,c='orange',s=8)
 else:xy.append(((x+xx)/2,(y+yy)/2))
ax.scatter(*zip(*xy),s=.1,c='#496b48',alpha=.3);ax.autoscale();ax.set_aspect('equal');ax.set_title('VMR MIF1 TT repair: actual legal placement, 5 resized south-band gates red');ax.set_xlabel('um');ax.set_ylabel('um');fig.tight_layout();fig.savefig('/tmp/qc-kits-vmr-review2.png',dpi=160)
