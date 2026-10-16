from pathlib import Path
import json
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).parent;b=json.loads((r/'leaf_blueprint.json').read_text());m=json.loads((r/'sizing.json').read_text());W,H=m['proposal']['outline_um'];fig,ax=plt.subplots(figsize=(13,6))
ax.add_patch(Rectangle((0,0),W,H,fill=False,lw=2))
for leaf in b['leaves']:
 x,y=leaf['home_um'];w,h=leaf['outline_um'];kind=leaf['name'].split('_')[0];col={'ingress':'#d9e7fa','format':'#dcefd5','return':'#f6d5d5'}[kind]
 ax.add_patch(Rectangle((x,y),w,h,ec='black',fc=col));label=leaf['name']+'\n'+str(leaf['payload_width'])+' bits' if'payload_width'in leaf else leaf['name']+'\n73 flops'
 ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=8)
ax.text(2,123,'21.6 um inter-row channel; independent physical clock entries at every child',fontsize=10)
ax.set_xlim(-8,W+8);ax.set_ylim(-8,H+8);ax.set_aspect('equal');ax.set_xlabel('Proposed parent x (um)');ax.set_ylabel('Proposed parent y (um)')
ax.set_title('S81 CFIFO structural sizing: 10 ingress + 9 output + return/control\nUNQUALIFIED proposal: real RTL cycle proof; parent ports/cuts/PG/clocks remain open')
fig.text(.07,.02,'Max root1054 sinks; +480 flops (+3.90%); 0 added RTL cycles. 47.52um ingress leaves reserve ~51.5% core fill at inherited post-CTS area/flop.\nFirst-pass footprint conflicts remain; no final placement/clock/route or native qualification. Return N→S physical connection needs explicit repair.',fontsize=10)
fig.tight_layout(rect=[0,.08,1,1]);fig.savefig(r/'partition_layout_proposal.png',dpi=150)
