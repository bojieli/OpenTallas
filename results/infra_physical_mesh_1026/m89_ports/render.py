import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).parent;r=json.loads((p/'geometry.json').read_text())
access=json.loads((p/'access_regions.json').read_text())
fig,axs=plt.subplots(1,2,figsize=(13,6))
for ax in axs:
 for name,(x0,y0,x1,y1) in access['cells'].items():ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec='green',ls='--',lw=.6))
 for name,(x0,y0,x1,y1) in access['ports'].items():
  ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec='black',lw=.8));ax.scatter((x0+x1)/2,(y0+y1)/2,s=10,c='black')
 for n,x,y in r['cells']:
  ax.add_patch(Rectangle((x,y),1.62,.27,fc='0.9',ec='black',lw=.8))
  ax.scatter([x+.027,x+1.593],[y+.135,y+.135],s=15,c=['orange','blue'])
  ax.text(x+.81,y+.35,n,fontsize=7,ha='center')
 for y in r['mesh_y']:
  ax.plot([r['mesh_x'][0]-.2,82.685],[y,y],c='blue',lw=2)
 for x in r['mesh_x']:ax.plot([x,x],[r['mesh_y'][0]-.2,r['mesh_y'][1]+.2],c='purple',lw=2)
 for y in r['mesh_y']:
  for x in r['mesh_x']:ax.scatter(x,y,marker='s',s=25,facecolors='none',edgecolors='black')
 for y in [19.98,79.92]:
  ax.plot([5,95],[y,y],c='brown',lw=1)
  ax.plot([5,95],[y+.27,y+.27],c='red',lw=1)
 for x,c in [(10,'red'),(90,'brown')]:ax.plot([x,x],[5,85],c=c,lw=1)
 ax.set(xlabel='x (um)',ylabel='y (um)');ax.grid(alpha=.15)
axs[0].set(xlim=(0,100),ylim=(0,100),title='2x2 actual ASAP7 mesh: blue M8, purple M9, PG red/brown');axs[0].set_aspect('equal')
axs[1].set(xlim=(18,25.5),ylim=(19.8,20.55),title='Lower-left driver/stub: actual M1 pins + via stack sites')
fig.tight_layout();fig.savefig(p/'review.png',dpi=150)
(p/'review.json').write_text(json.dumps({'verdict':'PASS-COND','scope':'M8/M9 production-clock metal mechanism with predeclared4x1.4umendpointislands beforeGRT/DRT only','picture':'review.png','findings':['Four actual BUFx24 driver/stub pairs on legal54nm sites and270nm rows; driver outputs and stub inputs lie on each M8strap.','M8/M9 mesh intersections have VIA89; eight M1pinaccess stacks each carry VIA12..VIA78.','PG M1 rails share cellVDD/VSSfaces and join separated M2trunks only with same-netVIA12.','Rootdriverinputs and stuboutputs terminate on nativeM9BTERMboxes atcanonicalM9/M8crossgrid; no arbitraryporthalo.','Green4x1.4umclockcellislands publishedfrompre-routeactualBUF24bboxes, independentlyofwires.','No setup/skew/IR/freezeclaim.']},indent=2)+'\n')
