"""Render review artifact from completed geometry/ports; never invokes an engine."""
import json,csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).resolve().parent
# Run after collection with output and canonical data next to this script.
g=json.loads((p/'out/geometry.json').read_text());ports=list(csv.DictReader((p/'ports.csv').open()))
fig,ax=plt.subplots(figsize=(11,10));ax.set_aspect('equal');D=140.4
ax.add_patch(Rectangle((0,0),D,D,fill=False,lw=2))
ax.add_patch(Rectangle((2.16,2.16),136.08,136.08,facecolor='#fafafa',edgecolor='gray'))
for i in range(504):
 y=2.16+i*.27;ax.plot([2.16,138.24],[y,y],color='#d5d5d5',lw=.12)
b=g['band'];ax.add_patch(Rectangle((b['xlo'],b['ylo']),b['xhi']-b['xlo'],b['yhi']-b['ylo'],facecolor='#b4d9ed',edgecolor='#387c9e',lw=1.5))
for role,color in [('input_data','#c66b32'),('registered_output','#1b7f65'),('clock','#ae258a')]:
 a=[r for r in ports if r['role']==role];ax.scatter([float(r['x_um']) for r in a],[float(r['y_um']) for r in a],s=3 if role!='clock' else 55,c=color,label=role,zorder=5)
ax.annotate('Clock source W(0,70.2); native CTS OPEN',(0,70.2),xytext=(8,90),arrowprops=dict(arrowstyle='->'),fontsize=10)
ax.text(70.2,120,'SOURCE / KIT MODEL — no cells placed',ha='center',fontsize=14,weight='bold')
ax.text(70.2,105,'All 504 legal rows retained; .054 × .270 µm sites\nOne connected FULLWIDTH allocation band; no FENCE',ha='center',fontsize=11)
ax.text(70.2,70.2,'104 whole rows: Y56.16..84.24 (28.08 µm)\n2904 real FF; 11145 native pre-CTS cells\nAllocation only: no individual cell coordinates',ha='center',va='center',fontsize=11)
ax.text(70.2,43,f"Native LEF area {g['physical_lef_area_um2']:.5f} µm²\nOrdinary band fill {g['band_fill_before_cts']*100:.3f}%; actual INT8 clock75.86 µm² ref {g['band_fill_with_INT8_reference']*100:.3f}%\nHeadroom to55% with measured clock reference: {g['additional_area_to_55pct_with_INT8_reference_um2']:.3f} µm²\nActual new CTS/hold/PG routing remain OPEN",ha='center',fontsize=11)
ax.text(70.2,25,'Whole-core fill8.91676%: ROOT pin-bound diagnostic exception\n2609 individually enumerated contacts; every face≤6/µm\nPG rail/contact MODEL only; actual connectivity/RC/timing OPEN',ha='center',fontsize=10)
for face,n in [('W',653),('N',652),('E',652),('S',652)]:
 xy={'N':(70.2,145),'S':(70.2,-6),'W':(-9,70.2),'E':(149,70.2)}[face];ax.text(*xy,f'{face}: {n}',ha='center',rotation=90 if face in 'WE' else 0)
ax.set_xlim(-15,157);ax.set_ylim(-12,151);ax.set_xlabel('µm');ax.set_ylabel('µm');ax.legend(loc='upper right',fontsize=8)
fig.tight_layout();fig.savefig(p/'SOURCE_KIT.png',dpi=180)
