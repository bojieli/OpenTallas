"""Artifact-only rendering of frozen model; power shapes omitted for legibility."""
import json,gzip,pathlib,collections
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
P=pathlib.Path(__file__).parent;plan=json.load(gzip.open(P/'site_plan.json.gz','rt'));a=json.load(open(P/'source_atoms.json'));j=json.load(open(P/'model.json'));strong=json.load(open(P/'stronger_sources.json'))['replacements'];b=json.load(gzip.open(P/'kit/inputs/positions.json.gz','rt'))
first={n for r in a for n in [z['cell'] for z in r['all_actual_new_sinks'] if z['cell'].startswith('int8_') and z['cell'].endswith('_hb0')]}
fig,(ax,detail)=plt.subplots(2,1,figsize=(15,10),gridspec_kw={'height_ratios':[3,1]});groups=collections.defaultdict(list)
for n,r in plan.items():
 q=r['bbox'];k='stronger source' if n in strong else 'first HB owned by source' if n in first else 'fresh clock' if n.startswith('MODEL_clock') else 'native state/signal and remaining HB'
 groups[k].append(Rectangle((q[0],q[1]),q[2]-q[0],q[3]-q[1]))
colors={'stronger source':'#ba283b','first HB owned by source':'#c48719','fresh clock':'#a43db0','native state/signal and remaining HB':'#54899f'}
for k,rs in groups.items():ax.add_collection(PatchCollection(rs,facecolor=colors[k],edgecolor='none'))
for name,ps in b['bterms'].items():
 if name in ('VDD','VSS'):continue
 for q in ps:
  for r in q['boxes']:ax.add_patch(Rectangle((r[1]/1000,r[2]/1000),max(.1,(r[3]-r[1])/1000),max(.1,(r[4]-r[2])/1000),color='#222'))
ax.add_patch(Rectangle((10.8,55.62),216,18.36,fill=False,edgecolor='#222'));ax.set(xlim=(0,237.6),ylim=(0,129.6),aspect='equal',xlabel='um',ylabel='um',title='Frozen INT8 source-owned / INVx6 refinement — SOURCE MODEL, BUILD REFUSED\n12,491 native cells; 1,669.29336 um²; 2,782 FF; 616 owned branches; no physical engine')
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([0],[0],marker='s',linestyle='',color=colors[k],label=f'{k}: {len(v)}') for k,v in groups.items()],loc='upper right',fontsize=8)
r=next(r for r in a if r['source_net']=='n5478');names={r['driver']['cell']}|{v['cell'] for v in r['all_actual_new_sinks']};bounds=[plan[n]['bbox'] for n in names]
for n in names:
 q=plan[n]['bbox'];detail.add_patch(Rectangle((q[0],q[1]),q[2]-q[0],q[3]-q[1],facecolor='#ba283b' if n==r['driver']['cell'] else '#c48719',edgecolor='white',lw=.7))
pts=[r['source_access_point_um']]+r['first_HB_native_pin_points_um'];detail.plot([v[0] for v in pts],[v[1] for v in pts],'k.',ms=4)
detail.set(xlim=(min(q[0] for q in bounds)-.1,max(q[2] for q in bounds)+.1),ylim=(min(q[1] for q in bounds)-.15,max(q[3] for q in bounds)+.15),aspect='equal',xlabel='um',ylabel='um',title=f'n5478: genuine INVx6 plus all ten first HB inputs; native LEF access-point centers\nShared-tree nominal wire {r["first_HB_only_nominal_wire_fF"]:.6f} fF; 0.5 fF is not a native feasibility limit')
fig.text(.07,.025,'Power shapes omitted from this signal-pin diagram for legibility; actual PG/access/conductor proof remains OPEN. All native rows/full-face signal pins retained.\nClock phases, actual wires/vias, native slew fixed point, SS setup/FF hold, complete all-driver census and joint route/clock/PG cut assignment remain unqualified.',fontsize=9)
fig.tight_layout(rect=[0,.07,1,1]);fig.savefig(P/'SOURCE_SIGNAL_MODEL.png',dpi=170)
