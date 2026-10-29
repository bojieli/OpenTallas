import json,re,gzip,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
D=Path(__file__).parent;p=json.load(gzip.open(D.parent/'plan_spine_raw.json.gz','rt'));reach=json.load(open(D/'actual_reach.json'))
sites={m[0]:(float(m[1]),float(m[2])) for m in re.findall(r'place_inst -name (\S+) -location \{([\d.]+) ([\d.]+)\}',(D/'ctree.tcl').read_text())}
fig,axs=plt.subplots(2,1,figsize=(13,8))
for ax,(lo,hi) in zip(axs,[(0,3000),(14500,17556.48)]):
 for q in p['partitions']:
  x,y=q['origin_um'];w,h=p['partition_types'][q['type']]['outline_um'];ax.add_patch(Rectangle((x,y),w,h,fc='#dde3eb',ec='#555',lw=.4))
 for ch in p['die']['channels']:
  x0,y0,x1,y1=ch['rect_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='#fff0a3',ec='none'))
 for e in reach['over']:
  a,b=sites[e['parent']],sites[e['child']];ax.plot([a[0],b[0]],[a[1],b[1]],'r-',lw=2)
 ax.scatter([v[0] for v in sites.values()],[v[1] for v in sites.values()],s=1,c='#333');ax.set_ylim(lo,hi);ax.set_xlim(0,17521.92);ax.set_aspect('equal')
axs[0].set_title('HK4 clock generation FAIL:26 stretched legs (red), up to745.04um\nClock legalizer excludes declared freed channels (yellow); no route launched')
fig.tight_layout();fig.savefig(D/'failure.png',dpi=120)
