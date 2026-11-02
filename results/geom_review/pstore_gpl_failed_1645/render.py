import json,csv,collections
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
P=Path(__file__).parent;d=json.load(open(P/'analysis.json'));cs=list(csv.DictReader((P/'placed.csv').open()))
f,axs=plt.subplots(1,3,figsize=(19,8),gridspec_kw={'width_ratios':[1.15,1.15,1]})
colors={'capture':'#2166ac','calendar':'#2b964a','relay':'#854dba','output':'#d34b35','cfg_forward':'#dd8a1b'}
for ax in axs[:2]:
 for c in cs:
  if c['kind']=='macro':ax.add_patch(Rectangle((float(c['x']),float(c['y'])),float(c['w']),float(c['h']),facecolor='#d8dce0',edgecolor='#777',linewidth=.4,zorder=1))
 ax.set(xlim=(0,673.92),ylim=(0,803.52),aspect='equal',xlabel='um',ylabel='um')
for kind in ['ungrouped']+list(colors):
 members=[c for c in cs if c['kind'] not in ('tap','macro') and (not c['region'] if kind=='ungrouped' else c['region'].endswith(kind))]
 axs[0].scatter([float(c['x'])+float(c['w'])/2 for c in members],[float(c['y'])+float(c['h'])/2 for c in members],s=.5 if kind=='ungrouped' else 1.6,c='#999' if kind=='ungrouped' else colors[kind],alpha=.3 if kind=='ungrouped' else .7,label=kind,zorder=3)
axs[0].set_title('ACTUAL failed GPL checkpoint (not DPL legal)\n44 macros; all51 real guide groups consumed');axs[0].legend(markerscale=5,fontsize=7,loc='upper right')
for r in d['regions']:
 k='cfg_forward' if r['name'].endswith('cfg_forward') else r['name'].split('_')[-1]
 b=r['rects'][0];axs[1].add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor=colors[k],lw=.8,alpha=.6,zorder=4))
axs[1].set_title('Actual region boxes: overlapping INCLUSIVE\nVOLTAGE_DOMAIN groups; no boxes widened')
sel=['ot_mrg_pstore_l4_output','ot_mrg_pstore_l9_output','ot_mrg_pstore_l8_output','ot_mrg_pstore_l5_calendar','ot_mrg_pstore_l0_capture']
for r in d['regions']:
 if r['name'] in sel:
  t=r['reported_trace'];axs[2].plot([v[0] for v in t],[v[1] for v in t],label=r['name'].replace('ot_mrg_pstore_',''))
axs[2].axhline(.1,c='black',lw=.6,ls='--');axs[2].set(xlabel='iteration',ylabel='reported regional overflow',title='Selected actual traces (not the unnamed2 warning IDs)\nHPWL +29.2658%; guards fired, no clearance')
axs[2].legend(fontsize=7)
f.suptitle('Pstore selector repair progressed; actual GPL0307 failure retained\n130394 instances; per-group actual member/available-row area<=5.05%, no empty group; numerical versus domain-overlap model remains to assess',fontsize=12)
f.tight_layout();f.savefig(P/'actual_failed_gpl.png',dpi=155,bbox_inches='tight')
