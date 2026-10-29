import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
r=Path('/srv/opentallas-scratch/claude/wt/codex-qc-a0-0251');children=json.loads((r/'physical/die_plan/qwen_compute/cores/a0/parent/nk_children.json').read_text())['children']
f,a=plt.subplots(figsize=(8,14));a.set_aspect('equal');a.add_patch(Rectangle((0,0),457.92,1157.76,fc='#fafafa',ec='black'))
for i,c in enumerate(children):
 x,y=c['at'];w,h=c['size_um'];isnode='node' in c['module'];a.add_patch(Rectangle((x-4.32,y-4.32),w+8.64,h+8.64,fill=False,ec='#bbb',lw=.5));a.add_patch(Rectangle((x,y),w,h,fc='#9bc6b8' if isnode else '#ced7e4',ec='#5c6775'));a.text(x+w/2,y+h/2,('NODE' if isnode else 'ROM' if 'romleaf' in c['module'] else 'RAW')+' '+str(i),ha='center',fontsize=7)
pts=[(457.878,669.996),(407.97,669.195),(208,820),(20,990)]
for j,(x,y) in enumerate(pts):a.scatter(x,y,s=50,c='#c64838');a.annotate(['rst input','root reset FF','NEW local reset FF','west status capture'][j],(x,y),xytext=(5,8),textcoords='offset points',fontsize=8)
for p,q in zip(pts,pts[1:]):a.plot([p[0],q[0]],[p[1],q[1]],c='#c64838',lw=2);a.text((p[0]+q[0])/2,(p[1]+q[1])/2,f'{abs(p[0]-q[0])+abs(p[1]-q[1]):.0f}um',fontsize=8)
a.set(xlim=(-5,470),ylim=(-5,1175),xlabel='um',ylabel='um',title='NK timed local output-reset plan: +1 boot edge, steady/data0\n19 actual SIGNED child sites; driver positions provisional until actual placement')
f.tight_layout();f.savefig('/srv/opentallas-scratch/claude/codex-qc-a0-0251/nk_reset_plan.png',dpi=140)
