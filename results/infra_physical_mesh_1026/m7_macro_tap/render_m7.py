import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).parent;g=json.loads((p/'geometry.json').read_text());c=json.loads((p/'access_regions.json').read_text())
fig,axs=plt.subplots(1,3,figsize=(16,6))
for ax in axs[:2]:
 ax.add_patch(Rectangle((26,21),8,8,fc='0.8',ec='black',alpha=.65));ax.text(30,28.2,'passive tap0\nM1-M7 OBS',fontsize=7,ha='center')
 for name,(x0,y0,x1,y1) in c['cells'].items():ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec='green',ls='--',lw=.6))
 for n,x,y in g['cells']:
  ax.add_patch(Rectangle((x,y),1.62,.27,fc='0.9',ec='black'));ax.text(x+.81,y+.4,n,fontsize=7,ha='center')
 for y in g['mesh_y']:ax.plot([g['mesh_x'][0]-.2,82.685],[y,y],c='blue',lw=2)
 for x in g['mesh_x']:ax.plot([x,x],[g['mesh_y'][0]-.2,g['mesh_y'][1]+.2],c='purple',lw=2)
 for n,(x0,y0,x1,y1) in c['ports'].items():
  ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fill=False,ec='black'));ax.scatter((x0+x1)/2,(y0+y1)/2,s=10,c='black')
 for y in [19.98,79.92]:ax.plot([5,95],[y,y],c='brown',lw=1);ax.plot([5,95],[y+.27,y+.27],c='red',lw=1)
 for x,color in [(10,'red'),(90,'brown')]:ax.plot([x,x],[5,85],c=color,lw=1)
axs[0].set(xlim=(0,100),ylim=(0,100),title='M9 root + native gen_phys M7 tap o0');axs[0].set_aspect('equal')
axs[1].set(xlim=(17,35),ylim=(19.2,30),title='All actualBUF24 cells outside opaque BLOCK')
x0,y0,x1,y1=c['terminals']['tap0/clk'];x=(x0+x1)/2;y=(y0+y1)/2;vy=.04+round((y-.04)/.08)*.08
axs[2].add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='0.92',ec='black',label='native M7 pin: 32x768nm'))
axs[2].add_patch(Rectangle((x-.016,vy-.027),.032,.054,fill=False,ec='orange',lw=2,label='VIA78 M7 enclosure:32x54nm'))
axs[2].add_patch(Rectangle((x-.027,vy-.020),.054,.040,fill=False,ec='blue',lw=1,label='VIA78 M8 enclosure'))
axs[2].axhline(vy,c='blue',ls='--',lw=.7);axs[2].set(xlim=(x-.10,x+.10),ylim=(y-.46,y+.46),title='M7 macro ITerm native box; no halo');axs[2].legend(fontsize=7,loc='upper right')
for ax in axs:ax.set_xlabel('x (um)');ax.set_ylabel('y (um)');ax.grid(alpha=.15)
fig.tight_layout();fig.savefig(p/'review.png',dpi=150)
(p/'review.json').write_text(json.dumps({'verdict':'PASS-COND','scope':'passive8x8partitionabstractM7ITerm32x768nmpinaccessregressionbeforeGRT/DRT','picture':'review.png','source_basis':'gen_phys.LAYER_W[M7]=.032;tapheight4*PIN_LEN_UM=.768;freshQCclockkittracksM7.032/.064andM8M9.04/.08','findings':['tap0/clk actualM7ITerm32x768nm can fully enclose nativeVIA78M7metal32x54nm.','Opaque8x8passiveBLOCKwithfullM1-M7OBS mirrorsgen_physpartitionabstract; all8topBUF24cellbboxesoutsideit.','Fixtureprovesmacroclockpinaccess only, NOTembeddedhardtypeclockownership.','ActualQC M7x.032+.064k; M8crossgridy.040+.080k(+8nmfromtapcenter); sourceM9root/othertapsunchanged.','ActualBUF24cellislands4x1.4um publishedbefore route; o0accessregionEXACTnativeM7box, nohalo.','Open channels and unchanged PG; anylower-layerescape is FAIL, no timing/skew/IR/freezeclaim.']},indent=2)+'\n')
