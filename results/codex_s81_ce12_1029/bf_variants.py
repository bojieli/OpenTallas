"""Prepare two source-only recipes and locality estimate from the retained V1 placement.

Estimates use actual lane acc_r cell centres. They are not new placed FFs or routes.
"""
from pathlib import Path
import json,re,statistics,sys,copy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

here=Path(__file__).resolve().parent
repo=here.parents[1]
base=json.loads((repo/'physical/die_plan/s81/cores/legacy/recipes.json').read_text())['ot_v41_bf_col']
lanes={i:[] for i in range(16)}
macros=[]
pattern=re.compile(r'g_l\\?\[(\d+)\\?\]')
for line in Path(sys.argv[1]).read_text().splitlines():
    a=line.split('\t')
    if a[0]=='C' and a[2]=='M':macros.append(tuple(map(float,a[4:8])))
    if a[0]!='C' or 'acc_r' not in a[-1]:continue
    m=pattern.search(a[-1])
    if m:
        lanes[int(m.group(1))].append(((float(a[4])+float(a[6]))/2,(float(a[5])+float(a[7]))/2))
assert [len(v) for v in lanes.values()]==[32]*16
recipes={};estimates=[]
fig,axes=plt.subplots(1,2,figsize=(15,5))
for groups,ax in zip((4,16),axes):
    rec=copy.deepcopy(base)
    rec['plan_module']='ot_v41_bf_col'
    rec['params']=dict(rec.get('params',{}),TAG_GROUPS=groups)
    rec['suffix']=f'ce12_tag{groups}'
    rec['_scope']='SOURCE PREPARATION ONLY. Fresh synth sink census, planned internal clock and visual placement review precede CTS/GRT.'
    recipes[f'ot_v41_bf_col_tag{groups}']=rec
    ax.add_patch(Rectangle((0,0),450.168,198.72,fill=False,lw=2))
    # Actual V1 ROM envelopes, not a proposed new macro relocation.
    for x0,y0,x1,y1 in macros:ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,color='gray',alpha=.4))
    rows=[]
    for group in range(groups):
        subset=range(group*(16//groups),(group+1)*(16//groups))
        pts=[p for l in subset for p in lanes[l]]
        x=statistics.median(p[0] for p in pts);y=statistics.median(p[1] for p in pts)
        raw=(x,y)
        xs={x};ys={y}
        for x0,y0,x1,y1 in macros:xs.update((x0-6,x1+6));ys.update((y0-6,y1+6))
        def legal(px,py):return 6<=px<=444.168 and 6<=py<=192.72 and not any(x0-6<px<x1+6 and y0-6<py<y1+6 for x0,y0,x1,y1 in macros)
        candidates=[(px,py) for px in xs for py in ys if legal(px,py)]
        x,y=min(candidates,key=lambda p:abs(p[0]-raw[0])+abs(p[1]-raw[1]))
        reach=max(abs(px-x)+abs(py-y) for px,py in pts)
        rows.append(dict(group=group,lanes=list(subset),accumulator_endpoints=len(pts),unconstrained_median_um=list(raw),candidate_legal_source_um=[x,y],max_centre_manhattan_um=reach))
        color=plt.cm.tab20(group/groups)
        ax.scatter([p[0] for p in pts],[p[1] for p in pts],s=5,color=color)
        ax.plot(x,y,'*',color=color,ms=11)
        for px,py in pts:ax.plot([x,px],[y,py],color=color,alpha=.06,lw=.5)
    estimates.append(dict(groups=groups,tag_width=13,delay=8,added_ff=13*(groups-1),clock_sink_delta_pct=100*13*(groups-1)/53852,cycle_delta=0,rows=rows,max_centre_manhattan_um=max(r['max_centre_manhattan_um'] for r in rows),qualification='ESTIMATE from retained actual cell centres; no clock/STA or full tag-net endpoint claim'))
    ax.set_title(f'{groups} final-stage copies: {16//groups} lanes/copy\nmax centre distance {estimates[-1]["max_centre_manhattan_um"]:.1f} µm')
    ax.set_aspect('equal');ax.set_xlim(-8,458);ax.set_ylim(-8,207);ax.grid(alpha=.2)
(here/'bf_tag_recipes.json').write_text(json.dumps(recipes,indent=2)+'\n')
(here/'bf_tag_estimate.json').write_text(json.dumps(estimates,indent=2)+'\n')
fig.suptitle('BF tag distribution proposals: current acc_r centres (dots), prospective final-tag sources (stars)\nSource placement estimate only. Original V1 macro positions shown; no new cells are placed.')
fig.tight_layout();fig.savefig(here/'bf_tag_review.png',dpi=150)
for e in estimates:print(e['groups'],e['max_centre_manhattan_um'],e['added_ff'])
