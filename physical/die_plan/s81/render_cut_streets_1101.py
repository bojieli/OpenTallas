#!/usr/bin/env python3
"""Focused floorplan review of explicit S81 cut-street reservation candidates."""
import json,sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plan=json.load(open(sys.argv[1]));report=json.load(open(sys.argv[2]));out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
parts={q['type']:q for q in plan['partitions']}
for page in range(3):
 fig,axs=plt.subplots(3,3,figsize=(15,14),dpi=140)
 for ax,tn in zip(axs.flat,sorted(report['bands'])[page*9:(page+1)*9]):
  t=plan['partition_types'][tn];q=parts[tn];w,h=t['outline_um'];ox,oy=q['origin_um'];ax.set(xlim=(-10,w+10),ylim=(-10,h+10));ax.set_aspect('equal');ax.set_title(q['name']+' / '+tn,fontsize=8)
  for b in report['bands'][tn]:
   a,c=b['span_um'];r=(0,a,w,c-a) if b['dir']=='EW' else (a,0,c-a,h)
   ax.add_patch(Rectangle(r[:2],r[2],r[3],fc='#e5a200' if b['layers'][0] in ('M4','M5') else '#b000c0',alpha=.5,lw=0))
  for hc in t.get('hard_cores',[]):
   a,b=hc['origin_um'];cw,ch=hc['outline_um']
   if hc.get('orient') in ('R90','R270','MXR90','MYR90'):cw,ch=ch,cw
   ax.add_patch(Rectangle((a,b),cw,ch,fc='#eeeeee',ec='#555555',lw=.5,alpha=.8))
  for slot in t.get('ft_slots',[]):
   regs=slot.get('regs_um') or []
   if regs:ax.plot([r[0] for r in regs],[r[1] for r in regs],c='#007f88',lw=.7,alpha=.7)
  for c in report['constraints']:
   if c['type']!=tn:continue
   if c['orient']=='horizontal':
    at=c['at_um']-oy
    if q.get('orient') in ('MX','R180'):at=h-at
    ax.axhline(at,color='red',lw=.6,ls='--')
   else:
    at=c['at_um']-ox
    if q.get('orient') in ('MY','R180'):at=w-at
    ax.axvline(at,color='red',lw=.6,ls='--')
  for tap in t.get('clock',{}).get('taps',[]):
   if tap.get('kind')!='core':ax.plot(*tap['xy'],marker='*',ms=2,c='#1255dd')
  ax.tick_params(labelsize=6)
 fig.suptitle('S81 explicit cut-street candidate: M4/M5 gold; M6/M7 purple; hard cores grey; FT register guides teal; critical cuts dashed red',fontsize=10)
 fig.tight_layout();path=out/f's81_cut_street_candidate_{page+1}_1101.png';fig.savefig(path);print(path)
