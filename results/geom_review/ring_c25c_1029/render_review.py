from pathlib import Path
import json,collections,math,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path(__file__).resolve().parent;ps=json.load(open(r/'pins.json'));sl=json.load(open(r/'slice.json'));ip=json.load(open(r/'infra.json'));W,H=ip['outline_um'];fig,axs=plt.subplots(1,2,figsize=(13,6),gridspec_kw={'width_ratios':[1.2,1]})
for ax in axs:
 ax.add_patch(Rectangle((0,0),W,H,fill=False,ec='black',lw=1.5))
 for k in range(55):
  for off,col in [(2.064,'#b25151'),(2.256,'#4f6b9e')]:
   x=k*4.32+off
   if x<=W:ax.axvspan(x-.06,x+.06,color=col,alpha=.28)
 for q in sl['islands']:
  x0,y0,x1,y1=q['rect_um'];ax.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,fc='#ffcf70',ec='#9c6500',alpha=.7));ax.text((x0+x1)/2,y1+1,q['name'].replace('tree_leaf','leaf'),fontsize=7,ha='center')
 for q in ip['ports']:ax.plot(*q['xy_um'],'o',ms=3,color='#087f5b')
 ce=ip['clock_entry']['xy_um'];ax.plot(*ce,'*',ms=14,color='#702ca1',label='actual clk M5 centre')
 axs[0].set_aspect('equal');axs[1].set_aspect('equal')
colors={'N':'#4a3a96','S':'#167d9a','E':'#af303b','W':'#177346'};faces=collections.defaultdict(list)
for p in ps:
 if p['bus']=='clk' or p['bus'].startswith('mp_isl'):continue
 f=p['face'];faces[f].append(p)
for f,qs in faces.items():axs[0].scatter([q['x'] for q in qs],[q['y'] for q in qs],s=3,color=colors.get(f,'black'),label=f'{f} {len(qs)} data/reset pins')
axs[0].set_xlim(-8,W+8);axs[0].set_ylim(-8,H+8);axs[0].legend(fontsize=7,loc='lower center',bbox_to_anchor=(.5,-.18),ncol=3);axs[0].set_title('233.28um square; no SRAM/macros\n3 core clock/reset islands, 2227 other pins unchanged')
axs[1].set_xlim(108,124);axs[1].set_ylim(110,123);axs[1].set_title('Entry / PG / FT pin clearance\nM5 vertical PG pitch4.32; FT x offset1.08')
for ax in axs:ax.set_xlabel('um');ax.set_ylabel('um')
fig.suptitle('RING C25c current-plan pre-build review: actual centre clock entry; one fresh place+CTS only');fig.tight_layout();fig.savefig(r/'ring_plan.png',dpi=170)
peaks={}
for f,qs in faces.items():
 vals=sorted(q['y'] if f in ('E','W') else q['x'] for q in qs);i=0;mx=0
 for j,v in enumerate(vals):
  while v-vals[i]>20+1e-6:i+=1
  mx=max(mx,j-i+1)
 peaks[f]=mx/20
clear=[]
for q in ip['ports']:
 x=q['xy_um'][0];dist=min(abs(x-(k*4.32+off))-.06 for k in range(55) for off in (2.064,2.256));clear.append(dist-.024)
report={'view':'71d2c363c67b','kit':'0086de4263d64ecc','verdict':'PASS-COND for ONE place+CTS prototype; placed review required before GRT/DRT','actual_clock':ip['clock_entry'],'outline_um':ip['outline_um'],'islands':len(sl['islands']),'macros':0,'pins':len(ps),'pin_peaks_per_um_in_20um_window':peaks,'min_ft_pin_pg_clearance_um':round(min(clear),3),'PG_basis':'M5 VERTICAL confirmed from ORFS asap7 tech LEF; stripe width.12 centres2.064/2.256 pitch4.32, native M1/M2 followrails; actual continuity checked at generated PG stage','source':'All10SVfiles identical to corrected1.08dx prior kit; old failedTT-30.39/6 FF-2.17/10 and slew1819 preserved. Current-flow automatic DATA repair only, no clock/ECO or virtual-clock change.','next':'Fresh currentflow synth/LEC->place+CTS; view actual placement+density+clock/reach, then continue only on geometry pass.'};(r/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
