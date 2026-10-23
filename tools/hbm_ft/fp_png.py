import sys, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.patches as pa
d=sys.argv[1]; out=sys.argv[2]
fig,ax=plt.subplots(figsize=(13,16.5))
rx=[];ry=[];rc=[]
for l in open(d+'/insts.tsv'):
    n,m,x,y,w,h=l.split('\t')[:6]; x,y,w,h=map(float,(x,y,w,h))
    if m.startswith('hbfd_'):
        rx.append(x);ry.append(y);rc.append('r' if 'rly' in m else 'b')
    elif max(w,h)>=450:
        ax.add_patch(pa.Rectangle((x,y),w,h,fc='0.85',ec='k',lw=0.4))
        ax.text(x+w/2,y+h/2,n,fontsize=5,ha='center',va='center')
ax.scatter(rx,ry,s=0.3,c=rc,lw=0)
ax.set_xlim(0,26200);ax.set_ylim(0,33200);ax.set_aspect('equal');fig.savefig(out,dpi=110,bbox_inches='tight')
