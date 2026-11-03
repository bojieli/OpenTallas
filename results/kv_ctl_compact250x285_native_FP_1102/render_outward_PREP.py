import json,gzip,csv
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
O=Path(__file__).resolve().parent;C=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-compact250-0430/collector');cells=list(csv.DictReader(open(C/'instances.csv')));f=json.loads(gzip.decompress((O/'FF_sites_outward_PREP.json.gz').read_bytes()));r=json.load(open(O/'FF_site_outward_PREP_report.json'));fig,aa=plt.subplots(1,2,figsize=(13,7))
for ax in aa:
 ax.set(xlim=(0,250.56),ylim=(0,285.12),xlabel='x um',ylabel='y um');ax.set_aspect('equal')
 for q in cells:
  if q['kind']=='macro':
   x,y,w,h=[float(q[k]) for k in ['x','y','w','h']];ax.add_patch(Rectangle((x,y),w,h,fill=False,ec='#999999',ls='--',lw=.9));nx=x+(-25.92 if x<100 else 25.92);ax.add_patch(Rectangle((nx-4.32,y-4.32),w+8.64,h+8.64,fill=False,ec='#3a956b',ls=':',lw=.7));ax.add_patch(Rectangle((nx,y),w,h,fc='#a1becb',ec='#33586f'));ax.annotate('',(nx+w/2,y+h/2),(x+w/2,y+h/2),arrowprops=dict(arrowstyle='->',color='#33586f',lw=1.8))
 ax.add_patch(Rectangle((120.76,138.04),9.04,9.04,fill=False,ec='red'));ax.plot(125.256,142.56,'*',c='red')
aa[0].annotate('85.944um clear central road',(125.3,97),xytext=(125.3,97),ha='center',fontsize=8);aa[0].plot([82.536,168.48],[97,97],c='#39845b',lw=2);aa[0].text(10,175,'21.6um\nedge road',rotation=90,fontsize=8);aa[0].text(235,175,'21.144um\nedge road',rotation=90,fontsize=8);aa[0].set_title('SPEC: outward columns ±25.92um\nDashed = actual current native macros')
aa[1].scatter([(p['ll_dbu'][0]+p['size_dbu'][0]/2)/1000 for p in f],[(p['ll_dbu'][1]+p['size_dbu'][1]/2)/1000 for p in f],s=.6,c='#116ab0');aa[1].set_title('Source-local FF PREP, no new native FP\nExisting/new-row intersection used conservatively')
fig.suptitle('CTL channel allocation PREP ONLY — no physical launch\nSource/outline/6849pins/6SRAMs/clock bay/cycles unchanged; new native rows/TAP/PG still OPEN',fontsize=12);fig.tight_layout();fig.savefig(O/'outward_columns_PREP_review.png',dpi=160)
