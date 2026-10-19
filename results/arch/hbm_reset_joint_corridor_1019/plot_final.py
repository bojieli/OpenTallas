import json
from pathlib import Path
import matplotlib;matplotlib.use('Agg');import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
O=Path(__file__).parent;a=json.load(open(O/'compressed_topology.json'));s=json.load(open(O/'sinks.json'));D={x['id']:x for x in a};fig,(ax,bx)=plt.subplots(1,2,figsize=(13,9),gridspec_kw={'width_ratios':[1.2,1]})
for n in a:
 if n['parent_id']==-1:continue
 p=D[n['parent_id']]['center_um'];pts=[p]+n['path_points'];ax.plot([x[0] for x in pts],[x[1] for x in pts],c='#6692b8',lw=.35)
ax.scatter([x['center_um'][0] for x in a],[x['center_um'][1] for x in a],s=2,c='#225b34');ax.scatter([x['xy_um'][0] for x in s],[x['xy_um'][1] for x in s],s=5,c='#c04a20');ax.scatter([11284.116],[15487.242],s=70,c='black',marker='*');ax.set(xlim=(0,20200),ylim=(0,31773.52),xlabel='um',ylabel='um',title='NEW dedicated HBM source MODEL\n2,263 native stations /810 boundary pins');ax.set_aspect('equal')
colors={'BUF':'#adcde5','FF':'#d8e5ae','INV':'#ecc49b','TIE':'#d5c8df'}
rows=[[("BUF",.972),("FF1",1.404),("INV1",.162),("FF2",1.404),("INV2",.162),("TIE",.162)],[("FFL1",1.404),("INVL1",.162),("FFL2",1.404),("INVL2",.162)]]
for j,row in enumerate(rows):
 x=0
 for name,w in row:
  typ=next(k for k in colors if name.startswith(k));bx.add_patch(Rectangle((x,j*.27),w,.27,facecolor=colors[typ],edgecolor='black',lw=.7));bx.text(x+w/2,j*.27+.135,name,ha='center',va='center',fontsize=7,rotation=90 if w<.3 else 0);x+=w
for y,col,role in [(0,'#194b8a','VSS'),(.27,'#af2e2e','VDD'),(.54,'#194b8a','VSS')]:bx.plot([0,8.424],[y,y],c=col,lw=2);bx.text(8.5,y,role,va='center',fontsize=8)
bx.add_patch(Rectangle((0,0),8.424,.54,fill=False,edgecolor='black',lw=1));bx.set(xlim=(-.3,9.2),ylim=(-.8,2.2),xlabel='um',yticks=[0,.27,.54],title='Proposed native ordinary-row body\n8.424 ×0.54um; R0 row0 /MX row1')
bx.text(0,1.9,'clock_out = native BUFx12f/Y\nreset_out = INV(FF2.QN)\nFF2.D = INV(FF1.QN); FF1.D = 1\nRESETN = upstream_reset_n; SETN = 1',fontsize=10,va='top');bx.text(0,-.2,'Native area: 3,024.31482um²; +5,514 FF\n31,108 new PG terminal bindings\nMax modeled reset/clock span: 402.6 /400.286um\nMax transparent reset /clock loads: 19 /6',fontsize=9,va='top')
fig.suptitle('SOURCE MODEL ONLY — actual PG, native OBS/track access, legal rows and TT/FF phase HOLD',fontsize=12);fig.tight_layout();fig.savefig(O/'JOINT_CORRIDOR_MODEL.png',dpi=150)
