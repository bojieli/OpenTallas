import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path
r=Path('/srv/opentallas-scratch/claude/wt/codex-qc-a0-0251');cs=json.loads((r/'physical/die_plan/qwen_compute/cores/a0/parent/nl_children.json').read_text())['children'];f,a=plt.subplots(figsize=(8,14));a.set_aspect('equal')
for c in cs:
 x,y=c['at'];w,h=c['size_um'];a.add_patch(Rectangle((x-4.32,y-4.32),w+8.64,h+8.64,fill=False,ec='#aaa',lw=.5));a.add_patch(Rectangle((x,y),w,h,fc='#ced7e4',ec='#667'))
 a.text(x+w/2,y+h/2,'ROM' if 'romleaf' in c['module'] else 'RAW',ha='center',fontsize=8)
a.plot([228.972]*2,[20,1135],c='#33868d',lw=3,alpha=.7)
for y in [140,270,400,530,660,820,990]:a.plot([15,442],[y,y],c='#33868d',lw=1.3,alpha=.7)
a.scatter(228.972,578.88,marker='*',s=160,c='#cc4534');a.annotate('Actual M5 ck entry\n228.972,578.880',(228.972,578.88),xytext=(5,15),textcoords='offset points',fontsize=9)
for xy,txt in [((442,590),'E tap command/payload capture'),((20,975),'W t_out status/payload capture')]:a.scatter(*xy,s=50,c='#a26323');a.annotate(txt,xy,xytext=(-190,20) if xy[0]>200 else (5,15),textcoords='offset points',fontsize=8)
a.annotate('ROM operand → RAW compute → W return',xy=(220,1040),xytext=(220,330),arrowprops=dict(arrowstyle='->',color='#a26323',lw=2),rotation=90,ha='center',fontsize=8,color='#84521e')
a.text(230,1165,'One unified ungated clock: parent FF +18 SIGNED child ETM\nICG=0 NL only. Native upper-layer selection; no DME meanders.',ha='center',fontsize=10)
a.set(xlim=(-5,470),ylim=(-5,1200),xlabel='um',ylabel='um',title='NL ICG0 unified data/clock plan (native prototype input / no clock cells yet)\nBlue upper-layer wire crossbars; driver sites only in legal streets')
f.tight_layout();f.savefig('/srv/opentallas-scratch/claude/codex-qc-a0-0251/nl_icg0_plan.png',dpi=140)
