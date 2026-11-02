from pathlib import Path
import json,csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
p=Path(__file__).parent
nodes={r['instance']:r for r in csv.DictReader((p/'actual_clock_nodes.tsv').open(),delimiter='\t')}
sinks={r['instance']+'/CLK':r for r in csv.DictReader((p/'actual_clock_sinks.tsv').open(),delimiter='\t')}
proposals=[json.loads((p/x/'leaf_sinks.json').read_text()) for x in ['current','cap16']]
fig,axes=plt.subplots(1,2,figsize=(14,7),constrained_layout=True)
for ax,assignment,label in zip(axes,proposals,['Actual placed original binding','Proposed same-fixed-node cap16 rebind']):
 seg=[];long=[];worst=0
 for leaf,names in assignment.items():
  n=nodes['mp_ck_'+leaf];start=(float(n['Y_x']),float(n['Y_y']))
  for name in names:
   s=sinks[name];end=(float(s['CLK_x']),float(s['CLK_y']));d=abs(start[0]-end[0])+abs(start[1]-end[1]);worst=max(worst,d)
   seg.append([start,end])
   if d>40:long.append([start,end])
 ax.add_collection(LineCollection(seg,colors='#267eb0',linewidths=.12,alpha=.11))
 ax.add_collection(LineCollection(long,colors='#e03d39',linewidths=.7,alpha=.8))
 ax.scatter([float(n['Y_x']) for n in nodes.values()],[float(n['Y_y']) for n in nodes.values()],s=.25,c='#121921',alpha=.35)
 ax.scatter([138.252],[138.240],s=70,c='#d39b00',marker='*',zorder=5)
 ax.set(xlim=(0,276.48),ylim=(0,276.48),aspect='equal',xlabel='um',ylabel='um',title=f'{label}\n34,225 native CLK pins; max L1 {worst:.3f} um; >40: {len(long)}')
 ax.grid(alpha=.12)
fig.suptitle('RED actual NEW placement: planning-only leaf net assignment; all 8,269 clock nodes fixed\nNative Y-to-CLK geometry; no database edits, CTS or absolute clock-frame qualification',fontsize=12)
fig.savefig(p/'actual_clk_rebind_plan.png',dpi=160)
