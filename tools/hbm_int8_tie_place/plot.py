import json,sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
j=json.load(open(sys.argv[1]));f,a=plt.subplots(figsize=(12,7));rect=[];colors=[]
for c in j['cells']:
 x,y,X,Y=c['box'];rect.append(Rectangle((x,y),X-x,Y-y));colors.append('#d62728' if c['master'].startswith('TIE') else '#167baa')
a.add_collection(PatchCollection(rect,facecolors=colors,linewidths=0))
for p in j['pins']:
 x,y,X,Y=p['box'];a.plot([(x+X)/2],[(y+Y)/2],'.',color='#222222',markersize=1)
x,y,X,Y=j['die'];a.set_xlim(x,X);a.set_ylim(y,Y);a.set_aspect('equal');a.set_xlabel('um');a.set_ylabel('um');a.set_title('INT8 SAFE t1: placement only; red = physical ties; no CTS or routed timing')
f.tight_layout();f.savefig(sys.argv[2],dpi=180)
