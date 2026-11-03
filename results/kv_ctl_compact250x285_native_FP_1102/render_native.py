import json,gzip,csv,collections,os
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import LineCollection
O=Path(__file__).resolve().parent;C=Path('/srv/opentallas-scratch/claude/codex-kv-ctl-compact250-0430/collector')
f=json.loads(gzip.decompress((O/os.environ.get('FF_SITE_FILE','FF_sites.json.gz')).read_bytes()));cells=list(csv.DictReader(open(C/'instances.csv')));rows=json.load(open(C/'rows.json'))['rows'];pg=list(csv.DictReader(open(C/'pg_boxes.csv')));r=json.load(open(O/os.environ.get('SITE_REPORT_FILE','FF_site_report.json')))
fig,aa=plt.subplots(1,3,figsize=(18,7))
for ax in aa:
 ax.set(xlim=(0,250.56),ylim=(0,285.12),xlabel='x (um)',ylabel='y (um)');ax.set_aspect('equal')
 for c in cells:
  if c['kind']=='macro':
   x,y,w,h=[float(c[k]) for k in ['x','y','w','h']];ax.add_patch(Rectangle((x-4.32,y-4.32),w+8.64,h+8.64,fill=False,ec='#539474',ls=':',lw=.6));ax.add_patch(Rectangle((x,y),w,h,fc='#94b1c0',ec='#365568'))
 ax.add_patch(Rectangle((120.76,138.04),9.04,9.04,fill=False,ec='red',lw=1));ax.plot(125.256,142.56,'*',c='red',ms=7)
a=aa[0];segments=[[(q['bbox'][0]/1000,q['bbox'][1]/1000),(q['bbox'][2]/1000,q['bbox'][1]/1000)] for q in rows];a.add_collection(LineCollection(segments,colors='#e3e3e3',linewidths=.2));tap=[c for c in cells if c['kind']=='tap'];a.scatter([float(c['x']) for c in tap],[float(c['y']) for c in tap],s=.35,c='#626262',alpha=.5);a.scatter([(q['ll_dbu'][0]+q['size_dbu'][0]/2)/1000 for q in f],[(q['ll_dbu'][1]+q['size_dbu'][1]/2)/1000 for q in f],s=.6,c='#116dbc');a.set_title('Actual native rows/TAPs + proposed 18,768 FFs\n6 LOCKED actual macros; no combinational placement')
a=aa[1];xs=[(q['ll_dbu'][0]+q['size_dbu'][0]/2)/1000 for q in f];ys=[(q['ll_dbu'][1]+q['size_dbu'][1]/2)/1000 for q in f];a.hist2d(xs,ys,bins=[71,80],range=[[0,250.56],[0,285.12]],cmap='YlOrRd');a.set_title(f"FF count per native-rule density bin\nFF-only empty {r['FF_only_density']['empty_area']}; later combs not counted")
a=aa[2]
for layer,color in [('M3','#c68d40'),('M5','#994e84')]:
 seg=[]
 for q in pg:
  if q['kind']=='metal' and q['layer']==layer:
   x0,y0,x1,y1=[float(q[k])/1000 for k in ['x0_dbu','y0_dbu','x1_dbu','y1_dbu']];seg.append([(x0,(y0+y1)/2),(x1,(y0+y1)/2)] if x1-x0>=y1-y0 else [((x0+x1)/2,y0),((x0+x1)/2,y1)])
 a.add_collection(LineCollection(seg,colors=color,linewidths=.3,alpha=.5,label=layer))
a.set_title('Actual native PG M3 landings + M5 stripes\nPG/via shadow must reduce signal capacity');a.legend()
fig.suptitle(f"CTL compact 250.56 × 285.12: NATIVE FP / FF MODEL ONLY — PLACE HELD\nR2R {r['R2R']['r2r_max']}um / 0 >405; public pin reach max145um / 0 >150; channels still OPEN",fontsize=13)
fig.tight_layout();fig.savefig(O/os.environ.get('IMAGE_FILE','native_FF_review.png'),dpi=160)
