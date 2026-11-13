import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path('/srv/opentallas-scratch2/claude/hard-s81-svc-1/packing_345.6.json');d=json.loads(p.read_text());W,H=d['outline_um']
fig,ax=plt.subplots(figsize=(8,14));ax.set(xlim=(0,W),ylim=(0,H),aspect='equal');ax.add_patch(Rectangle((0,0),W,H,fill=False))
colors={'head':'#91bee3','sx':'#ecce8d','sml':'#adc797','smd':'#adc797','smc':'#adc797','smr':'#adc797','h4':'#caa4d4','trx':'#dbb193'}
for b in d['placements']:
 n=b['name'];k=next(k for k in colors if n.startswith(k));ax.add_patch(Rectangle((b['x'],b['y']),b['w'],b['h'],facecolor=colors[k],edgecolor='black'));ax.text(b['x']+b['w']/2,b['y']+b['h']/2,n,ha='center',va='center',fontsize=7)
ax.add_patch(Rectangle((34.56,H-34.56-328.32),W-69.12,328.32,facecolor='#dddddd',edgecolor='black'));ax.text(W/2,H-34.56-164.16,'Assumed S_att control + memory\n328.32 um; source cut not built',ha='center',va='center')
ax.set_title('Packing only: +345.60 um Y; 8.64 um origin grid\n43.20 um streets, 34.56 um edges; pin/data flow unqualified');fig.savefig(p.with_suffix('.png'),dpi=140)
