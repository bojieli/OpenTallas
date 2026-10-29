from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path('/srv/opentallas-scratch/claude/codex-ring-nearmiss-1029');cells={}
for l in Path('/tmp/ring-routed.tsv').read_text().splitlines():
 a=l.split('\t')
 if a[0]=='C':cells[a[8].replace('\\','')]=(a[3],*map(float,a[4:8]))
ends=json.loads((r/'negative_hold_endpoints.json').read_text())['endpoints']
fig,(ax,z)=plt.subplots(1,2,figsize=(13,6));ax.scatter([(v[1]+v[3])/2 for v in cells.values()],[(v[2]+v[4])/2 for v in cells.values()],s=.07,c='#777777',rasterized=True)
for x in ends:
 v=cells[x['endpoint'].rsplit('/',1)[0]];ax.plot(v[1]-1.08,v[2],'ro',ms=3)
for name in ['u_bin_qid/q[1]$_DFF_P_','u_bin_qid/_3_']:
 v=cells[name];ax.add_patch(Rectangle((v[1],v[2]),v[3]-v[1],v[4]-v[2],fc='orange',ec='orange'));ax.annotate(name,(v[1],v[2]),xytext=(20 if 'q[' in name else 30,v[2]+8),arrowprops={'arrowstyle':'->'},fontsize=8)
ax.arrow(7.3,186.7,0,-69.66,color='green',head_width=3,length_includes_head=True);ax.set(xlim=(0,233.28),ylim=(0,233.28),aspect='equal',title='Actual routed data homes; red = 16 proposed capture pads')
for name,v in cells.items():
 if v[1]<11 and v[3]>4 and v[2]<119 and v[4]>115:
  clk=name.startswith('clk');z.add_patch(Rectangle((v[1],v[2]),v[3]-v[1],v[4]-v[2],fc='#4466aa' if clk else '#cccccc',ec='white',lw=.3))
z.add_patch(Rectangle((6.372,116.91),.702,.27,fc='#44aa44',ec='black',lw=.8));z.annotate('INVx11 in free row slot',(6.723,117.045),xytext=(7.1,118.35),arrowprops={'arrowstyle':'->'},fontsize=9)
z.set(xlim=(4,11),ylim=(115,119),aspect='equal',title='Proposed local qid[1] inverter; all clocks / FF homes fixed')
for a in (ax,z):a.set_xlabel('um');a.set_ylabel('um')
fig.tight_layout();fig.savefig(r/'rcxfix_proposal.png',dpi=160)
