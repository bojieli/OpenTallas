import json,pathlib,runpy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
D=runpy.run_path(str(pathlib.Path(__file__).with_name('pin_plan.py')))
R=json.load(open('/srv/opentallas-scratch/claude/su-native-candidate1030/native_su_pinplan_report.json'))
fig,axs=plt.subplots(2,2,figsize=(14,12))
for ax,(module,report)in zip(axs.flat,R['modules'].items()):
 W,H=report['outline_um'];pts,macros,_=D['build'](module,W,H)
 ax.add_patch(Rectangle((0,0),W,H,fill=False))
 for m in macros:
  x,y=m['xy_um'];ax.add_patch(Rectangle((x,y),D['MW'],D['MH'],facecolor='#b9c8de',edgecolor='black'));ax.text(x+3,y+18,str(m['bank'])+'/'+str(m['reader'])+' '+m['orient'],fontsize=7)
 for face,color in [('N','#2166ac'),('S','#2166ac'),('W','#b2182b'),('E','#b2182b'),('C','#1b7837')]:
  p=[p for p in pts if p['face']==face];ax.scatter([q['x']for q in p],[q['y']for q in p],s=2,c=color)
 ax.add_patch(Rectangle((W/2-4.32,H/2-4.32),8.64,8.64,fill=False,edgecolor='green'))
 ax.set_title(module.replace('ot_hbm_su_static_pgslice_lg__','')+'\n'+str(report['pins'])+' pins; read reach bound '+str(report['macro_read_to_planned_boundary_ff_upper_bound_um'])+'um',fontsize=10)
 ax.set_aspect('equal');ax.set_xlim(-8,W+8);ax.set_ylim(-8,H+8)
fig.suptitle('CURRENT NATIVE SU ABI pin/macro PREP — no adoption / no PNR\nblue inputs; red outputs; green clock + distinct reset roles; banks/readers labelled',fontsize=13)
fig.tight_layout();fig.savefig(pathlib.Path(__file__).with_name('native_pinplan.png'),dpi=150)
