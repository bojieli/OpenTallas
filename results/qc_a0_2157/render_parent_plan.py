#!/usr/bin/env python3
import json,pathlib,sys
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
here=pathlib.Path(__file__).resolve().parent;root=here.parents[1];out=here/'parent_plan'
colors={'romleaf':'#72a6c8','lsl':'#8dbb87','node':'#cdad7e'}
dims={'romleaf':(172.8,110.16),'lsl':(99.792,140.4),'node':(47.52,432)}
def kind(c):return 'romleaf' if 'romleaf' in c['view'] else ('node' if 'node' in c['view'] else 'lsl')
fig,axs=plt.subplots(1,4,figsize=(15,12))
for pair,k in enumerate(['nk','nl']):
 p=json.loads((out/f'{k}_plan.json').read_text());base=json.loads((root/f'tools/qwen_romleaf/a0core/specs/qfd_tile_{k}_a0cv8.json').read_text());t0=json.loads((root/f'tools/qwen_romleaf/a0core/a0c8_{k}_taps.json').read_text())['taps']
 for after in [False,True]:
  ax=axs[2*pair+int(after)];s=p['spec'] if after else base;ts=p['taps'] if after else t0
  ax.set_xlim(-8,466);ax.set_ylim(-8,1170);ax.set_aspect('equal');ax.add_patch(Rectangle((0,0),457.92,1157.76,fill=False,lw=1.1))
  ax.add_patch(Rectangle((200.664,16.776),56.592,641.664,color='#f5e3a5',alpha=.55))
  for i,c in enumerate(s['children']):
   x,y=c['at'];w,h=dims[kind(c)];ax.add_patch(Rectangle((x-5.4,y-5.4),w+10.8,h+10.8,fill=False,ls=':',ec='#666666',lw=.7));ax.add_patch(Rectangle((x,y),w,h,color=colors[kind(c)],alpha=.7))
   if kind(c)=='lsl':
    import re
    j=re.search(r'g_sl\[(\d+)\]',c['inst']).group(1);ax.text(x+w/2,y+h/2,'LSL'+j+'\n'+('NEW\nplanned' if after else 'FP1\nlegacy'),ha='center',va='center',fontsize=7)
    px=x if c['orient']=='MY' else x+w;ax.plot([px,px],[y+5,y+h-5],c='#17537c',lw=1.7)
   elif kind(c)=='romleaf':
    ax.text(x+w/2,y+h/2,'ROM',ha='center',va='center',fontsize=8);px=x+w if c['orient']=='MY' else x;ax.plot([px,px],[y+5,y+h-5],c='#17537c',lw=1.7)
   else:ax.text(x+w/2,y+h/2,'node\nlegacy',ha='center',va='center',fontsize=7,rotation=90)
  for t in ts:ax.scatter(*t['xy'],s=10,color='#ca6d21',zorder=4)
  for m in p['moves']:
   if after and 'pin'in m:ax.annotate('',xy=m['to'],xytext=m['from'],arrowprops={'arrowstyle':'->','color':'#a52b37','lw':.8})
  ax.set_title(k.upper()+' '+('MODE3/sync candidate' if after else 'v8 template (MODE9/FP1)'),fontsize=10)
  ax.set_xlabel('um');ax.tick_params(labelsize=8)
axs[0].set_ylabel('um')
fig.suptitle('A0 parent planning only — no adoption or P&R\n10.8um middle-LSL relief; clock pins outside child halos; all die/data face pins retained',fontsize=13,y=.98)
fig.text(.04,.045,'Dotted:5.4um halos | Blue:child data pin faces | Orange:planned clock taps | Yellow:geometric corridor only (capacity unproved).\nLSL new view absent; ROM/node historical views require source/reset/clock qualification. Clock budgets TT250/FF202.5ps are proposals, not measured insertion.\nPDN and exact MODE3 placed buses/sinks must be reviewed before physical execution; no R6/MODE9 endpoint credit.',fontsize=9)
fig.subplots_adjust(left=.04,right=.99,top=.91,bottom=.10,wspace=.23);fig.savefig(out/'a0_parent_geometry.png',dpi=160)
