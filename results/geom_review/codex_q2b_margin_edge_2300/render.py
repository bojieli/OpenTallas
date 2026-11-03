from pathlib import Path
import json,re
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).parent;o=json.load(open(p/'codex_prep2252.json'))
fig,(a,b)=plt.subplots(1,2,figsize=(15,5),gridspec_kw={'width_ratios':[1,1.4]})
a.add_patch(Rectangle((15.12,13.26),94.824,41.064,facecolor='#e2e8f0',edgecolor='black'));a.text(61,42,'Actual SRAM0 FS\nsolid M3 obstruction',ha='center',fontsize=9)
a.scatter([15.132],[28.488],c='#059669',s=35);a.annotate('M4 rd_out[252]',(15.132,28.488),xytext=(21,33),arrowprops={'arrowstyle':'->'},fontsize=8)
a.add_patch(Rectangle((8.748,27.54),.4,.27,facecolor='#2563eb'));a.annotate('Existing B4 BUF at8.748,27.540\nBUFx2 -> BUFx4 (PREP)',(8.748,27.54),xytext=(-3,46),arrowprops={'arrowstyle':'->'},fontsize=8)
a.scatter([118.638],[24.84],c='#7c3aed',s=25);a.annotate('Actual row1[252] capture\n118.638,24.840',(118.638,24.84),xytext=(79,5),arrowprops={'arrowstyle':'->'},fontsize=8)
for net,s in o['nets'].items():
 if 'codex_q2_force_B_4' not in net:continue
 for frag in re.split(r' NEW ',s):
  pts=re.findall(r'\(\s*([\d*]+)\s+([\d*]+)\s*\)',frag);xy=[];x=y=None
  for xx,yy in pts:
   x=x if xx=='*' else int(xx)/1000;y=y if yy=='*' else int(yy)/1000
   if x is not None and y is not None:xy.append((x,y))
  if len(xy)>1:a.plot(*zip(*xy),color='#2563eb',alpha=.6,lw=.7)
a.set_xlim(-5,128);a.set_ylim(0,59);a.set_aspect('equal');a.set_title('Existing pin/data geometry; one driver upgrade')
colors=['#2563eb','#d97706']
for c,(name,s) in zip(colors,list(o['nets'].items())[:1]+[(k,v) for k,v in o['nets'].items() if k=='net11317']):
 for frag in re.split(r' NEW ',s):
  if not frag.startswith('M3 '):continue
  pts=re.findall(r'\(\s*([\d*]+)\s+([\d*]+)\s*\)',frag);xy=[];x=y=None
  for xx,yy in pts:
   x=x if xx=='*' else int(xx)/1000;y=y if yy=='*' else int(yy)/1000
   if x is not None and y is not None:xy.append((x,y))
  if len(xy)>1:b.plot(*zip(*xy),color=c,lw=1)
b.axhspan(13.26,13.4,color='#cbd5e1');b.text(23.3,13.34,'Actual SRAM solid M3 OBS',ha='center',fontsize=9)
b.axhspan(13.224,13.26,color='#fca5a5',alpha=.8);b.text(23.3,13.244,'Proposed 36nm M3 edge lip',ha='center',fontsize=8)
for x in [20.061,20.241,27.513]:
 b.add_patch(Rectangle((x-.009,13.244),.018,.016,facecolor='red'));b.scatter([x],[13.23],s=15,c='red');b.plot([x,x],[13.149,13.179],color='#059669',lw=3)
b.axhline(13.23,color='red',ls='--',lw=.8);b.text(25.5,13.234,'Old M2 track + VIA23',fontsize=8)
b.axhline(13.149,color='#059669',ls='--',lw=1);b.text(24.5,13.154,'Legal lower M2 row track (PREP)',fontsize=8)
b.set_xlim(19.7,28);b.set_ylim(13.10,13.4);b.set_title('Actual three M3 markers and proposed legal access track');b.set_xlabel('um');b.set_ylabel('um')
a.set_xlabel('um');a.set_ylabel('um');fig.suptitle('q2 forceB PREP only: TT slew344.72>320 +3M3 spacing; preserve failed route and all clocks')
fig.tight_layout();fig.savefig(p/'q2b_margin_edge_prep.png',dpi=160)
