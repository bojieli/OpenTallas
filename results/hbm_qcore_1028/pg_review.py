"""Render and check the actual PG/track pin repair, before the approved trial."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
src=Path('/srv/opentallas-scratch/claude/codex-qcore-1028/pg_audit.log')
out=Path(__file__).parent
pins={};pg=[]
for line in src.read_text().splitlines():
 a=line.split()
 if a and a[0]=='PIN':pins[a[1]]=list(map(float,a[3:]))
 if a and a[0]=='PG':pg.append((a[1],*map(float,a[3:])))
xs={0:[150.120,152.280],1:[55.080,57.240],2:[167.400,169.560]}
records=[]
fig,axes=plt.subplots(1,3,figsize=(13,6))
for g,(cx,cy)in enumerate([(151.2,112.32),(56.16,86.4),(168.48,103.68)]):
 ax=axes[g]
 for n,x0,y0,x1,y1 in pg:
  if x0<cx+3 and x1>cx-3:
   ax.add_patch(Rectangle((x0,cy-4),(x1-x0),8,color='crimson'if n=='VDD'else'royalblue',alpha=.3))
 for n,b in pins.items():
  if not n.startswith(f'mp_isl{g}_'):continue
  old=(b[0]+b[2])/2;nx=xs[g][0 if n.endswith('_i')else 1]
  nb=[nx-(b[2]-b[0])/2,b[1],nx+(b[2]-b[0])/2,b[3]]
  assert abs((nx-.024)/.048-round((nx-.024)/.048))<1e-7
  gaps=[max(x0-nb[2],nb[0]-x1,0)for _,x0,y0,x1,y1 in pg if y0<nb[3]and y1>nb[1]]
  clearance=min(gaps)
  assert clearance>.9
  ax.add_patch(Rectangle((b[0],b[1]),b[2]-b[0],b[3]-b[1],fill=False,edgecolor='magenta',lw=2))
  ax.add_patch(Rectangle((nb[0],nb[1]),nb[2]-nb[0],nb[3]-nb[1],fill=False,edgecolor='green',lw=2))
  records.append({'name':n,'old_box_um':b,'new_box_um':nb,'old_x':old,'new_x':nx,'new_pg_clearance_um':clearance,'new_on_M5_track':True})
 ax.set(xlim=(cx-3, cx+3),ylim=(cy-3.5,cy+3.5),aspect='equal',title=f'Island{g}: PG blue/red, old magenta, new green',xlabel='um')
fig.tight_layout();fig.savefig(out/'pg_review.png',dpi=160)
(out/'pin_delta.json').write_text(json.dumps({'status':'TRIAL_ONLY_APPROVED_PG_FIX','pins':records,'functional_clock_pin_unchanged':[151.176,112.32],'all_infra_cells_unchanged':True,'M5_track_offset_pitch_um':[.024,.048]},indent=2)+'\n')
