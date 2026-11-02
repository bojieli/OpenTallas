import sys,json,copy,collections
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/die_plan'))
from schema import Plan
from check import check_cuts,Report,lane_geometry
source=Path('/srv/opentallas-scratch/claude/codex-current-ci-2049/physical/die_plan/qwen_kvsys/plan_of_record/plan_c.json')
import die_trial as D
D.ROOT=source.parents[4]
raw=json.loads(source.read_text()); out=Path(__file__).parent
rows={}
for tag,share in [('current',None),('north_channel_PREP_ONLY',True)]:
    a=copy.deepcopy(raw)
    changed=[]
    if share:
        en={p['type'] for p in a['partitions'] if p['name'].startswith('hgi_EN_')}
        wn={p['type'] for p in a['partitions'] if p['name'].startswith('hgi_WN_')}
        for tn in sorted(en|wn):
            t=a['partition_types'][tn]
            gaps=[[0,17.28],[233.28,336.96],[552.96,656.64],[872.64,976.32],[1192.32,1278.72]]
            roads=[dict(dir='NS',span_um=g,layers=['M5','M7'] if tn in en else ['M5'],die_share=.4 if tn in en else .61) for g in gaps]
            t['die_ft_bands']=roads if tn in en else copy.deepcopy(t.get('die_ft_bands',[]))+roads
            changed.append(tn)
        (out/'north_channel_PREP_ONLY.json').write_text(json.dumps({'status':'PREP ONLY; not activated; frozen masters untouched','type_band_delta':{tn:a['partition_types'][tn]['die_ft_bands'] for tn in changed}},indent=2)+'\n')
    P=Plan(a,path=source);geo={l:lane_geometry(P,l) for l in P.lanes};R=Report();c=check_cuts(P,R,geo)
    rows[tag]=dict(findings=R.items,cuts=c,changed_types=changed)
    if not share:
        details=[]
        for pn,cut in [('hgi_EN_0',25500),('hgi_EN_6',15750),('hgi_WN_7',14250)]:
            rect=P.rect(pn); hits=[]
            for lid,(pts,*_) in geo.items():
                for p,q in zip(pts,pts[1:]):
                    if min(p[1],q[1])<cut<max(p[1],q[1]) and rect[0]<=p[0]<=rect[2]:
                        lane=P.lanes[lid];hits.append(dict(lane=lid,width=P.ports[lane['ports'][0]]['width'],ports=lane['ports']))
            details.append(dict(part=pn,cut=cut,bits=sum(h['width'] for h in hits),segments=len(hits),unique_lanes=len(set(h['lane'] for h in hits)),lanes=sorted(hits,key=lambda h:-h['width'])))
        rows[tag]['actual_cut_lanes']=details
(out/'cut_analysis.json').write_text(json.dumps(rows,indent=2)+'\n')
# View uses true local core placement; no geometry proposal or plan mutation.
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
T=raw['partition_types']['kv3_hgi_v3'];w,h=T['outline_um'];fig,ax=plt.subplots(figsize=(9,8))
ax.add_patch(Rectangle((0,0),w,h,facecolor='#e5f5f9',edgecolor='black'))
for c in T['hard_cores']:
    x,y=c['origin_um'];cw,ch=c['outline_um'];ax.add_patch(Rectangle((x,y),cw,ch,facecolor='#777777',edgecolor='white'));ax.text(x+cw/2,y+ch/2,c['inst'],ha='center',va='center',fontsize=7,color='white')
ax.axhline(100,ls='--',c='red');ax.text(w/2,275,'Representative cut: four 216 um core columns blocked',ha='center',fontsize=9)
ax.set(xlim=(-15,w+15),ylim=(-15,h+15),xlabel='Local x (um)',ylabel='Local y (um)',title='Current HGI footprint / existing M5,M7 vertical corridors\nNo outline, core, station or pin movement proposed')
ax.set_aspect('equal');fig.text(.5,.015,'Open width 414.72 um; current 25% share: 3780 tracks.\nEN PREP-only 40% reserved share: 6048 tracks; 3623 / 6048 = 0.5990.\nWN needs M5 61% + existing M7 50%: 8510.4 tracks; 5055 / 8510.4 = 0.5940.',ha='center',fontsize=10)
fig.subplots_adjust(bottom=.14);fig.savefig(out/'hgi_corridors.png',dpi=140)
print({k:(len(v['findings']),v['cuts']['worst_partition_segment'],len(v['changed_types'])) for k,v in rows.items()})
