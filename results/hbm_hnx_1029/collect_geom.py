import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/autopilot'));import geom_rules as G
D=G.Design(sys.argv[1]);P=Path(__file__).parent;tag=sys.argv[2];r=G.r2r_metrics(D);print(r,flush=True);json.dump(r,open(P/(tag+'_r2r.json'),'w'),indent=2)
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
f,a=plt.subplots(figsize=(8,8));a.set(xlim=(0,285.12),ylim=(0,302.4),aspect='equal');a.add_collection(PatchCollection([Rectangle((c[2],c[3]),c[4]-c[2],c[5]-c[3])for c in D.cells.values()if c[0]=='S'],facecolor='#2e7f66',linewidth=0,alpha=.4));c=next(c for c in D.cells.values()if c[6]=='u_bdc.jv$_DFF_PN0_');x,y=G.ctr(c);a.plot(x,y,'ro',ms=7);a.annotate('jv anchor',(x,y),xytext=(130,240),arrowprops=dict(arrowstyle='->'));a.set_title('HNX actual '+tag+' successor\n37757 captures; max'+str(r['r2r_max'])+'um; '+str(r['r2r_captures_gt405'])+' above405');f.tight_layout();f.savefig(P/(tag+'.png'),dpi=140)
