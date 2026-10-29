"""Render native clock homes + exact plan hard bodies and planned PG gaps."""
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as p,json,sys
from matplotlib.patches import Rectangle
T=json.load(open(sys.argv[1]));R=json.load(open(sys.argv[2]));F=json.load(open(sys.argv[3]));fig,ax=p.subplots(1,2,figsize=(12,10));q=list(T['sites'].values())
for kind,a,b,c,d in F:ax[0].add_patch(Rectangle((a/1000,b/1000),(c-a)/1000,(d-b)/1000,color='gray',alpha=.18))
ax[0].scatter([a for a,b in q],[b for a,b in q],s=.3);ax[0].set_title('15,296 native clock bodies + hard boundaries')
x,y=q[0];ax[1].set_xlim(x-22,x+22);ax[1].set_ylim(y-15,y+15)
for net,l,a,b,c,d in R:
 if a<x+22 and c>x-22 and b<y+15 and d>y-15:ax[1].add_patch(Rectangle((a,b),c-a,d-b,color='orange' if l=='M8' else 'gray',alpha=.4))
for a,b in q:
 if abs(a-x)<22 and abs(b-y)<15:ax[1].add_patch(Rectangle((a,b),1.62,.27,color='blue'))
ax[1].set_title('Native root body in planned upper-PG gaps')
for a in ax:a.set_aspect('equal');a.set_xlabel('um');a.set_ylabel('um')
fig.tight_layout();fig.savefig(sys.argv[4],dpi=170)
