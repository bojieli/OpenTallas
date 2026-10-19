import json,gzip,pathlib
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
P=pathlib.Path(__file__).parent;A=json.load(open(P/'allowlist.json'));B=json.load(gzip.open(P/'inputs/positions.json.gz','rt'))
fig,ax=plt.subplots(figsize=(15,9));groups={k:[] for k in ['unchanged','FF','clock','replacement','addition']}
clock={r['instance'] for r in json.load(open(P/'inputs/clock_cost.json'))['rows']}
for n,r in B['insts'].items():
 if n in A['placement']:continue
 k='clock' if n in clock else 'FF' if r['master'].startswith('DFF') else 'unchanged'
 x,y,X,Y=r['bbox'];groups[k].append(Rectangle((x/1000,y/1000),(X-x)/1000,(Y-y)/1000))
for n,r in A['placement'].items():
 x,y,X,Y=r['bbox'];groups['replacement' if n in A['replacement_cells'] else 'addition'].append(Rectangle((x/1000,y/1000),(X-x)/1000,(Y-y)/1000))
colors=dict(unchanged='#b9bec4',FF='#4387bf',clock='#8d3fa6',replacement='#dd8b21',addition='#25a45d')
for k,v in groups.items():ax.add_collection(PatchCollection(v,facecolor=colors[k],edgecolor='none',label=f'{k}: {len(v)}',alpha=.9))
for n,ps in B['bterms'].items():
 if n in ('VDD','VSS'):continue
 for p in ps:
  for layer,x,y,X,Y in p['boxes']:ax.add_patch(Rectangle((x/1000,y/1000),max(.10,(X-x)/1000),max(.10,(Y-y)/1000),facecolor='#161616'))
ax.set_xlim(0,237.6);ax.set_ylim(0,129.6);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um')
ax.set_title('INT8 exact offline ECO placement MODEL — NO native mutation / placement / CTS / route\n1078 replacements +1866 additions; all2782 FF and253 clock cells fixed')
from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([0],[0],marker='s',linestyle='',color=colors[k],label=f'{k}: {len(v)}') for k,v in groups.items()],loc='upper right',fontsize=9)
fig.text(.10,.035,'237.6×129.6 um; 464 original legal rows; 1667.54376 um² cells (5.41534% outline).\nFull-face .192 um pins retained; reach bound367.2 um. Native row orientation/PG contacts/RC and292 lower-cap source nets remain OPEN.',fontsize=10)
fig.tight_layout(rect=[0,.08,1,1]);fig.savefig(P.parent/'placement_MODEL.png',dpi=180,bbox_inches='tight')
