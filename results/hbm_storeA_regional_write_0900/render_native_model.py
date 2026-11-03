from pathlib import Path
import json,csv
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).resolve().parent
MOD='ot_hnx_sfu_store_a_regional4_captured'
mac=json.loads((R/'core_macros.json').read_text())['cores'][MOD]['macros'];pins=json.loads((R/'native_pins.json').read_text());rows=list(csv.DictReader((R/'capture_capacity_rows.csv').open()))
fig,ax=plt.subplots(figsize=(13,9));colors=['#a6cee3','#b2df8a','#fdbf6f','#cab2d6']
for m in mac:
 x,y,xx,yy=m['rect_um'];idx=0 if '.m0.' in m['name'] else 2
 import re
 b=int(re.search(r'\[(\d+)\]',m['name']).group(1));region=idx+(b//2)%2
 ax.add_patch(Rectangle((x-4.32,y-4.32),xx-x+8.64,yy-y+8.64,facecolor='pink',alpha=.3))
 ax.add_patch(Rectangle((x,y),xx-x,yy-y,facecolor=colors[region],edgecolor='grey',alpha=.65))
 ax.text((x+xx)/2,(y+yy)/2,f'm{idx//2} b{b}',ha='center',va='center',fontsize=7)
ax.scatter([float(q['x_um']) for q in rows],[float(q['y_um']) for q in rows],s=.4,c='#dd6600',label='8800 simultaneous capture prototype cells, not mapped')
raw=[p for p in pins if p['name'].startswith(('capture_payload_D','capture_meta87_D'))]
ax.scatter([q['x']for q in raw],[q['y']for q in raw],s=.8,c='black',label='2200 raw D/metadata M4 pin model')
clk=next(q for q in pins if q['name']=='store0_clk[0]');ax.scatter([clk['x']],[clk['y']],marker='*',s=160,c='gold',edgecolor='black',label='M5 clock entry reference; tree/PG/timing held')
for m in range(2):
 for c in range(2):
  x=195 if c==0 else 558;y=116 if m==0 else 324
  ax.annotate('',xy=(x,y),xytext=(375,220),arrowprops=dict(arrowstyle='->',color='#666666',alpha=.5))
ax.set_xlim(0,760.32);ax.set_ylim(0,483.84);ax.set_aspect('equal');ax.set_xlabel('Core x (um)');ax.set_ylabel('Core y (um)')
ax.set_title('Disabled StoreA source-only native intake model: 32 real SRAMs, 5986 ABI\n4 column regions / 8800 same-edge capture copies / +0 cycles\nOld read/combinational cells, actual Q/D paths, clock/reset/PG/parent source joins unplaced')
ax.legend(loc='upper center',bbox_to_anchor=(.5,-.1),fontsize=8);fig.tight_layout();fig.savefig(R/'native_source_model.png',dpi=150,bbox_inches='tight')
