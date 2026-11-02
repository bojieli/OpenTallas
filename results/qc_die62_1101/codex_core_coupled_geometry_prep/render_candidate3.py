import gzip,json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
B=Path(__file__).resolve().parent;c=B/'candidate3';r=json.load(open(B/'candidate2/CANDIDATE_REVIEW.json'));f=json.load(open(B/'candidate2/PF_CAPTURE_PARTIAL_GEOMETRY.json'));p=json.load(gzip.open(c/'DISABLED_PARENT_PLAN_UNRELEASED.json.gz'))
fig,(ax,pa)=plt.subplots(1,2,figsize=(14,11),gridspec_kw={'width_ratios':[1.1,1]})
for h in r['macros']:
 x,y=h['origin_um'];w,z=h['outline_um'];a=h['halo_um'];fold=h['module']=='ot_coll_fold_slice';ax.add_patch(Rectangle((x-a,y-a),w+2*a,z+2*a,fill=False,ec='#999',lw=.5));ax.add_patch(Rectangle((x,y),w,z,color='#89b4d8'if fold else'#d9bf8d',ec='black',lw=.6));lab=h['inst'].split('.u_coll.')[-1]if fold else h['inst'].split('.')[-2];ax.text(x+w/2,y+z/2,lab,ha='center',va='center',fontsize=6,rotation=90 if h['orient']=='R90'else 0)
ax.scatter([z['proposed_center_um'][0]for z in f['rows']],[z['proposed_center_um'][1]for z in f['rows']],s=1,color='#168b4d')
ax.set(xlim=(0,760.32),ylim=(0,1036.8),aspect='equal',xlabel='CORE x (um)',ylabel='CORE y (um)',title='29 actual/reference bodies + halos;1024 existing PF homes\nPartial paths402.744/402.813um; complete source HOLD')
colors={'coll_core':'#89b4d8','coll_ucie':'#b2d8b5','coll_ft__cla4a25d77':'#d8c7eb','coll_ftm':'#eab0a2','phy_ucie_kv':'#d4d4d4','glue':'#eeeeee'}
for part in p['partitions']:
 if part['name']not in ['coll_f0','coll_f1','coll_f2','coll_core','coll_f3','coll_ucie','ucie_kv','glue']:continue
 x,y=part['origin_um'];w,h=p['partition_types'][part['type']]['outline_um'];pa.add_patch(Rectangle((x,y),w,h,color=colors.get(part['type'],'#eeeeee'),ec='black',lw=.6));pa.text(x+w/2,max(6250,y+h/2),part['name'],ha='center',va='center',fontsize=8,clip_on=True)
pa.set(xlim=(-50,1700),ylim=(6200,11600),aspect='equal',xlabel='die x (um)',ylabel='die y (um)',title='Candidate3: unchanged sharedFT/PHY/glue/dieedge\nFTm expands; W/E public windows stay globally fixed')
fig.suptitle('DISABLED source proposal — R90 tool support/full graph/model+boot remain HOLD; no GEN/P&R',fontsize=12);fig.tight_layout();fig.savefig(c/'review_candidate3.png',dpi=145)
