import json,pathlib,tkinter,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
p=pathlib.Path('/home/ubuntu/coord/tmp/codex-qbs-sites-2320');t=tkinter.Tcl();sys.path.insert(0,str(p/'tooltree/tools/die_plan'));import core_infra as CI
for mod in ['dsfd_node_LLfu','dsfd_node_LLfd','dsfd_node_NNfu']:
 d=p/mod;tech=json.load(open(d/'technology.json'));sl=json.load(open(d/'legalized_slice.json'));fig,axs=plt.subplots(1,2,figsize=(12,9),gridspec_kw={'width_ratios':[1,1]})
 for ax,zoom in zip(axs,[False,True]):
  for kind,color,alpha in [('pg','#e5a534',.28),('fixed','#574740',.7),('face','#547fc1',.65)]:
   patches=[]
   for o in tech['obstacles']:
    if o['kind']!=kind:continue
    a,b,c,e=[x/tech['dbu'] for x in o['rect']]
    if zoom and (c<20 or a>23 or e<37 or b>40.4):continue
    patches.append(Rectangle((a,b),c-a,e-b))
   ax.add_collection(PatchCollection(patches,facecolor=color,edgecolor='none',alpha=alpha))
  for row in tech['rows']:
   a,b,c,e=[x/tech['dbu'] for x in row['rect']]
   if zoom and 37<b<40.4:ax.axhline(b,color='gray',lw=.35,alpha=.5)
  poses=sl['cell_placements'];xy={n:x['centre_um'] for n,x in poses.items()};xy['port:clk']=sl['islands'][0]['clock_pin']['xy_um']
  for n in sl['core_tree']['nodes']:
   q=poses[n['name']];a,b=q['origin_um'];w,h=q['size_um'];ax.add_patch(Rectangle((a,b),w,h,fc='#32a45c',ec='black',lw=.5,zorder=8));x,y=q['centre_um'];aa=xy[n['parent']];
   bb=[x,y];corner=next(z for z in [(x,aa[1]),(aa[0],y)] if not CI._seg_hits(*( (aa,z) if z[1]==aa[1] else (z,bb)),sl['pg_obstructions_um']['M4']) and not CI._seg_hits(*( (z,bb) if z[1]==aa[1] else (aa,z)),sl['pg_obstructions_um']['M5']));ax.plot([aa[0],corner[0],x],[aa[1],corner[1],y],color='#aa2040',lw=.7,zorder=6)
   if (not zoom and not n['name'].startswith('qb_entry')) or (zoom and n['name'].startswith('qb_entry')):ax.text(x,y+.25,n['name'].replace('qb_entry_','e'),fontsize=6,ha='center',zorder=9)
  a,b,c,e=sl['islands'][0]['rect_um'];ax.add_patch(Rectangle((a,b),c-a,e-b,fill=False,ec='purple',ls='--',lw=.8));cx,cy=xy['port:clk'];ax.scatter([cx],[cy],marker='s',s=16,color='red',zorder=10)
  ax.set_aspect('equal');ax.set(xlabel='µm',ylabel='µm')
  if zoom:ax.set(xlim=(20,23.2),ylim=(37.3,40.3),title='Exact owned bay replaced by preGPL cells')
  else:ax.set(xlim=(0,43.2),ylim=(0,77.76),title='Actual TAP/face/PG + planned legal clock tree')
 fig.suptitle(f'{mod}: 13 planned cells, actual rows/.054µm sites, PG PASS13/13; source-stage plan only');fig.tight_layout();fig.savefig(d/'actual_pg_legalized_plan.png',dpi=160)
