import json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent;d=json.load(open(P/'guide_estimate.json'));infra=json.load(open(sys.argv[1]));f,a=plt.subplots(figsize=(8,8));a.set_xlim(0,391.392);a.set_ylim(0,416.448);a.set_aspect('equal')
a.add_patch(Rectangle((148.446,203.1),94.8,41.1,fc='#8ebbe5',ec='#235a83',label='fixed SRAM'))
for box in {tuple(x['rect_um'])for x in infra['cells']}:
 x,y,xx,yy=box;a.add_patch(Rectangle((x,y),xx-x,yy-y,fc='#eeaaaa',ec='#a94444'))
for m in d['moves']:
 x,y=m['old_xy_um'];xx,yy=m['new_xy_um'];a.plot([x,xx],[y,yy],lw=.3,c='#999999',alpha=.5);a.plot(xx,yy,'.',ms=2,c='#008855');a.add_patch(Rectangle((xx-4.32,yy-4.32),8.64,8.64,fill=False,ec='#008855',lw=.35))
a.set_title('CTLX same-outline locality estimate\n165 movable registers; full-graph centre reach385um; P&R not yet run');a.set_xlabel('um');a.set_ylabel('um');f.tight_layout();f.savefig(P/'guide_estimate.png',dpi=150)
