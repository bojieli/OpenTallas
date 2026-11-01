#!/usr/bin/env python3
"""Read-only completed RED placement and actual clock-sink overlay."""
import argparse,csv,json,collections
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--csv',type=Path,required=True);p.add_argument('--geo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rows=list(csv.DictReader(a.csv.open()));xy=lambda q:(float(q['x'])+float(q['w'])/2,float(q['y'])+float(q['h'])/2)
active=[q for q in rows if q['kind'] in ['std','buf','ff']];clocks=[q for q in rows if q['name'].startswith('red_ck')];sinks=[]
for l in a.geo.open():
 f=l.split()
 if f and f[0]=='SINK':sinks.append(dict(x=float(f[1]),y=float(f[2]),master=f[3],instance=f[4],pin=f[5]))
assert len(clocks)==649 and len(sinks)==34225
fig,axes=plt.subplots(1,2,figsize=(14,7))
for ax in axes:ax.set_aspect('equal');ax.set_xlim(0,276.48);ax.set_ylim(0,276.48);ax.set_xlabel('µm');ax.set_ylabel('µm');ax.grid(alpha=.1)
axes[0].hist2d(*zip(*(xy(q) for q in active)),bins=70,range=[[0,276.48],[0,276.48]],cmap='Blues');axes[0].set_title('Actual completed3_place component-origin counts\n(excludes taps/pins; not cell-area utilization)')
axes[1].scatter([q['x'] for q in sinks],[q['y'] for q in sinks],s=.15,c='#6289ad',alpha=.35,label='34225 actual native clock sinks');axes[1].scatter(*zip(*(xy(q) for q in clocks)),s=8,c='#bf4c35',label='649 actual red_ck seed cells');axes[1].scatter([138.24],[138.24],marker='*',s=70,c='black',label='public ck center entry');axes[1].legend(fontsize=8);axes[1].set_title('Actual placed sink / seed-clock overlay\nSeed topology is NOT qualified NLDM or CTS')
fig.suptitle('Unsigned RED native HARD_PINREG child276.48² — actual PLACE LOOK, CTS remains HELD');fig.tight_layout();fig.savefig(a.out/'actual_red_place_clock.png',dpi=150)
s=dict(schema='opentallas.qc.red.actual_place_clock_review.v1',outline_um=[276.48,276.48],actual_placed_components_by_kind=dict(collections.Counter(q['kind'] for q in rows)),actual_native_clock_sinks=len(sinks),sink_master_counts=dict(collections.Counter(q['master'] for q in sinks)),seed_clock_cells=len(clocks),clock_entry_um=[138.24,138.24],sink_bbox_um=[min(q['x'] for q in sinks),min(q['y'] for q in sinks),max(q['x'] for q in sinks),max(q['y'] for q in sinks)],scope='actual placement and sink census only; active model unqualified, no CTS/GRT/signoff approval')
(a.out/'actual_summary.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s,indent=2))
