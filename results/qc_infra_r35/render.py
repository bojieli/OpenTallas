import json,sys
sys.path.insert(0,'tools/tools/die_plan')
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import schema as S, die_trial as DT
from pathlib import Path
P=S.Plan(S.load('die_plan_sliceclk.json'),Path('die_plan_sliceclk.json')); site=DT.SiteMap(P)
J=json.load(open('qc_slice_rows.json'))
col={'TOP':'tab:red'}
def draw(ax,xl,yl,lw):
    for (a,b,c,d) in site.parts: ax.add_patch(Rectangle((a,b),c-a,d-b,fill=False,lw=0.2,ec='0.7'))
    for r in site.forb: ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],fc='0.85',ec='none'))
    for r in J['reservations']:
        c='tab:red' if r['cls']=='TOP' else ('tab:green' if r['role'].startswith('leg') else 'tab:blue' if r['layer']=='M9' else 'tab:purple')
        if r['layer']=='M8': ax.plot([r['lo'],r['hi']],[r['centre_um']]*2,c=c,lw=lw)
        else: ax.plot([r['centre_um']]*2,[r['lo'],r['hi']],c=c,lw=lw)
    ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect('equal')
f,ax=plt.subplots(1,3,figsize=(30,11))
draw(ax[0],(0,P.W),(0,P.H),0.8); ax[0].set_title('QC slice clock reservation: TOP red (M8 rows 1520-1525 + HUB M9 feed), column M9 blue, node rows purple, legs green; grey = hard cores+halo')
draw(ax[1],(16300,19000),(0,P.H),1.2); ax[1].set_title('E0 slice + W0 edge')
draw(ax[2],(17550,18400),(12150,13350),1.5); ax[2].set_title('E0 zoom: leg 7 (y 12312), top band (13124-13176), root jog row 1519, column')
plt.tight_layout(); plt.savefig('qc_slice_rows.png',dpi=70)
