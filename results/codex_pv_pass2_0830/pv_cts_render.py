import json,sys,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
k=sys.argv[1];x=json.load(open(k+'/pv_cts_tree.json'));fig,ax=plt.subplots(figsize=(8,8));ax.add_collection(LineCollection(x['edges'],colors='royalblue',linewidths=.35,alpha=.5))
s=x['clock_sinks'];ax.scatter([a[0] for a in s],[a[1] for a in s],s=.2,c='green',alpha=.2);bb=x['clock_buffers'];ax.scatter([a[0] for a in bb],[a[1] for a in bb],s=2,c='blue');ax.scatter([86.427],[86.535],s=45,c='red',label='approved1xBUFx4 root')
ax.set_xlim(0,172.8);ax.set_ylim(0,172.8);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um');ax.set_title('PV join '+k.split('/')[-1]+' actual CTS placement topology\n'+str(len(x['edges']))+' buffer edges; '+str(len(s))+' clock sink loads; lines show connectivity');ax.legend(loc='lower right');fig.tight_layout();fig.savefig(k+'/pv_cts_tree.png',dpi=150)
