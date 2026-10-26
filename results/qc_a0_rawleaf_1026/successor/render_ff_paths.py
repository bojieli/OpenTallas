from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import math
plt.rcParams['text.parse_math']=False
r=Path('/srv/opentallas-scratch/claude/wt/codex-qc-a0-1026/results/qc_a0_rawleaf_1026/successor/cts')
rows=[x.split('\t') for x in (r/'cts_placed_inst.tsv').read_text().splitlines()]
norm=lambda x:x.replace('\\','')
cells={norm(v[0]):(v[1],tuple(map(float,v[2:6]))) for v in rows}
pins={norm(v[0]):tuple(map(float,v[2:4])) for v in (x.split('\t') for x in (r.parent/'place/placed_pin.tsv').read_text().splitlines())}
clocks={norm(v[0]):float(v[3]) for v in (x.split('\t') for x in (r/'clock_FF.tsv').read_text().splitlines())}
cases=[('scalar','first_d','u_ls.s3_first$_DFF_P_',-55.283661,'Scalar input: in_min = -40 ps; hold uncertainty 12.5 ps'),('internal','u_ls.g_grp[1].g_lane[1].g_ladd.u_add.g_nr.u.s1_code[18]$_DFF_P_','u_ls.g_grp[1].g_lane[1].g_ladd.u_add.g_nr.u.u_cb.g_r.r[82]$_DFF_P_',-6.398021,'Internal data path: hold uncertainty 25 ps')]
for tag,s,e,slack,basis in cases:
 def ctr(n):
  if n in pins:return pins[n]
  _,(x0,y0,x1,y1)=cells[n];return ((x0+x1)/2,(y0+y1)/2)
 sx,sy=ctr(s);ex,ey=ctr(e);dist=abs(sx-ex)+abs(sy-ey)
 pad=max(3,dist*.45);xmin=max(0,min(sx,ex)-pad);xmax=min(115.344,max(sx,ex)+pad);ymin=max(0,min(sy,ey)-pad);ymax=min(140.4,max(sy,ey)+pad)
 fig,ax=plt.subplots(figsize=(9,7))
 for n,(m,box) in cells.items():
  x0,y0,x1,y1=box
  if x1<xmin or x0>xmax or y1<ymin or y0>ymax:continue
  ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor='#b9c9d4' if m.startswith('DFF') else '#dddddd',edgecolor='#b7b7b7',lw=.3))
 for n,c in [(s,'#2076ae'),(e,'#ca3428')]:
  if n in cells:
   _,(x0,y0,x1,y1)=cells[n];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor=c,edgecolor='black',lw=1))
 ax.scatter([sx],[sy],c='#2076ae',s=70,zorder=5);ax.scatter([ex],[ey],c='#ca3428',s=70,zorder=5)
 ax.annotate('',xy=(ex,ey),xytext=(sx,sy),arrowprops=dict(arrowstyle='->',color='#ca3428',lw=1.8))
 ax.annotate('launch / input'+(f'\nCK {clocks[s]:.3f} ps' if s in clocks else ''),(sx,sy),xytext=(-85,-40),textcoords='offset points',fontsize=9)
 ax.annotate(f'capture\nCK {clocks[e]:.3f} ps',(ex,ey),xytext=(12,25),textcoords='offset points',fontsize=9)
 ax.set_xlim(xmin,xmax);ax.set_ylim(ymin,ymax);ax.set_aspect('equal');ax.set_xlabel('um');ax.set_ylabel('um')
 ax.set_title(f'Actual A0 leaf FF hold family: {slack:+.3f} ps\n{basis}\nEndpoint Manhattan distance {dist:.3f} um (4_cts_pg geometry)')
 fig.subplots_adjust(bottom=.20)
 fig.text(.03,.11,'Start: '+s,fontsize=7);fig.text(.03,.075,'End:   '+e,fontsize=7)
 fig.text(.03,.035,'833 ps, 60/25 ps; actual TT/FF pin references 171.234/139.086 ps; generated IO40 vector contract unchanged',fontsize=8)
 fig.savefig(r/f'ff_{tag}_path.png',dpi=150)
 print(tag,'distance',dist,'start_xy',(sx,sy),'end_xy',(ex,ey))
