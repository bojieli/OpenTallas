from pathlib import Path
import json,csv,collections
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle
R=Path(__file__).parent;d=json.loads((R/'render_inputs.json').read_text())['sle_su_c'];ts=json.loads((R/'model.json').read_text())['new_tap_rows'];taps={'ot_proto_clk_'+str(j):(t[1],t[2]) for j,t in enumerate(ts)}
g=collections.defaultdict(list)
for a in csv.DictReader((R/'ot_tap_chain_groups.tsv').open(),delimiter='\t'):g[a['group']].append(a)
segments=[];colors=[]
for rows in g.values():
 for a in rows:
  xy=(float(a['x_um']),float(a['y_um']));segments.append([taps[a['tap']],xy]);colors.append(int(a['tap'].rsplit('_',1)[1])%20)
fig,axes=plt.subplots(1,2,figsize=(12,9),gridspec_kw={'width_ratios':[1,1.3]})
for ax in axes:
 for hc in d['hard_cores']:
  x,y=hc['origin_um'];w,h=hc['outline_um'];ax.add_patch(Rectangle((x,y),w,h,facecolor='#d9dde2',edgecolor='#8a9098',lw=.35))
 ax.add_collection(LineCollection(segments,array=colors,cmap='tab20',linewidths=.24,alpha=.32))
 ax.scatter([x for x,y in taps.values()],[y for x,y in taps.values()],s=13,color='black',marker='+',zorder=5)
 ax.set_aspect('equal');ax.set_xlabel('µm');ax.set_ylabel('µm');ax.grid(alpha=.15)
axes[0].set_xlim(0,d['outline_um'][0]);axes[0].set_ylim(0,d['outline_um'][1]);axes[0].set_title('Actual placement + 81 proposed tap positions')
rows=max(g.values(),key=lambda rows:len(rows));xy=[(float(a['x_um']),float(a['y_um'])) for a in rows];x,y=taps[rows[0]['tap']];xy+=[(x,y)];xs,ys=zip(*xy)
axes[1].set_xlim(min(xs)-45,max(xs)+45);axes[1].set_ylim(min(ys)-45,max(ys)+45);axes[1].set_title(f'One actual joined chain ({len(rows)} registers)')
axes[1].scatter([float(a['x_um']) for a in rows],[float(a['y_um']) for a in rows],s=17,color='#ce3434',zorder=7)
axes[1].annotate(rows[0]['tap'],(x,y),xytext=(8,8),textcoords='offset points',fontsize=8)
fig.suptitle('EAST SUc bounded chain affinity — assignment prototype\nB2: 547 joined segments / 2,932 clock moves; zero new boundaries vs A81; max reach 199.720 µm',fontsize=12)
fig.text(.5,.015,'Lines are clock assignments, not routed wires. Original placed cells/macros preserved. No CTS, PG or timing sign-off credit.',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.035,1,.93));fig.savefig(R/'affinity_geometry.png',dpi=140)
