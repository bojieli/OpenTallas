import json,sys,collections,math
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
R0=Path(__file__).parent;sys.path.insert(0,str(R0/'tools_actual2/die_plan'));import schema as S,die_trial as D
sys.path.insert(0,str(R0));import clock_reach_frozen as F
R=R0/'actual_sm3_fast';P=S.Plan(S.load('/srv/opentallas-scratch2/claude/codex-hbm-pins-1028/street4/die_plan.json'));T=json.load(open(R/'tree.json'));summary=json.load(open(R/'summary.json'));T['meta']['physical_dme']=F.freeze_sites(T,405.);(R/'tree_frozen.json').write_text(json.dumps(T,indent=1));reach=F.actual_reach(T,405.)
occ=collections.defaultdict(list);over=[]
for n,(x,y) in T['sites'].items():
 box=(x,y,x+1.62,y+.27);keys=[(i,j)for i in range(int(x//8.64),int((x+1.62)//8.64)+1)for j in range(int(y//8.64),int((y+.27)//8.64)+1)];seen=set()
 for k in keys:
  for m,b in occ[k]:
   if m in seen:continue
   seen.add(m)
   if box[0]<b[2]-1e-8 and b[0]<box[2]-1e-8 and box[1]<b[3]-1e-8 and b[1]<box[3]-1e-8:over.append([n,m])
 for k in keys:occ[k].append((n,box))
rowbad=[n for n,p in T['sites'].items()if abs(p[0]/.054-round(p[0]/.054))>1e-5 or abs(p[1]/.54-round(p[1]/.54))>1e-5]
site=D.SiteMap(P);hits=[]
for n,(x,y) in T['sites'].items():
 for r in site.forb:
  if x<r[2]-1e-8 and x+1.62>r[0]+1e-8 and y<r[3]-1e-8 and y+.27>r[1]+1e-8:hits.append([n,r]);break
rep=dict(scope='clock coupon only, noPNR/STA',cells=len(T['sites']),row_errors=rowbad,body_overlaps=over,macro_PG_halo_hits=hits,reach=reach,model_window_ps=summary['window_ps']);(R/'body_review.json').write_text(json.dumps(rep,indent=1))
fig,ax=plt.subplots(figsize=(15,12));part='NW_sm3';p=P.parts[part];typ=P.types[p['type']];ox,oy=p['origin_um'];w,h=typ['outline_um'];ax.add_patch(plt.Rectangle((ox,oy),w,h,fc='#fafafa',ec='black',lw=1))
for c in typ['hard_cores']:
 x,y=c['origin_um'];cw,ch=c['outline_um'];a,b=P.to_die(part,(x,y)),P.to_die(part,(x+cw,y+ch));ax.add_patch(plt.Rectangle((min(a[0],b[0]),min(a[1],b[1])),abs(a[0]-b[0]),abs(a[1]-b[1]),fc='#ddd',ec='#888',lw=.5));ax.text((a[0]+b[0])/2,(a[1]+b[1])/2,c['inst'],ha='center',va='center',fontsize=5,rotation=90)
xy=T['sites'];ax.add_collection(LineCollection([(xy[c],xy[p])for c,p in T['parent_of'].items()],colors='#2e6a9e',lw=.6));ax.scatter([p[0]for p in xy.values()],[p[1]for p in xy.values()],s=5,c='#dc711d',label='nativeclockcells');ax.scatter([t['xy'][0]for t in T['taps']],[t['xy'][1]for t in T['taps']],s=32,marker='x',c='black',label='34actualclockentries');ax.set_xlim(ox-120,ox+w+120);ax.set_ylim(oy-120,oy+h+120);ax.set_aspect('equal');ax.legend(loc='upper right');ax.set_title(f'HBM NW_sm3 frozenclockcoupon: 34taps/{len(xy)}cells; maxhop{reach["worst_um"]:.2f}um; MODEL TT{summary["window_ps"]["TT"]:.2f}/FF{summary["window_ps"]["FF"]:.2f}ps\nNo route or STA; footprint/rows/forbidden-body checks only');fig.savefig(R/'geometry.png',dpi=120,bbox_inches='tight');print(json.dumps({k:(len(v)if isinstance(v,list)else v)for k,v in rep.items()},indent=1))
