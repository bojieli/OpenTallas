#!/usr/bin/env python3
"""Planning-only diagram of the exact selected r10 producer and disabled relocation frontier."""
import argparse,json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT=Path(__file__).resolve().parents[2]
r=ROOT/'results/hbm_programme_source_frontier_0146'
ap=argparse.ArgumentParser();ap.add_argument('--candidate-y',type=float,default=17.28);ap.add_argument('--out',type=Path,default=r/'programme_source_frontier.png');args=ap.parse_args()
if args.out.exists():raise SystemExit('fresh image path required; preserve previous candidate')
plan=Path('/home/ubuntu/coord/tmp/codex-hbm-su00-upper-clock-2335/composite_root_PENDING.json')
a=json.loads(plan.read_text());t=a['partition_types']['q_b113'];fig,axs=plt.subplots(1,2,figsize=(15,7));ax=axs[0]
for name,color in [('NW_hub','#edf2f8'),('NW_b113','#e1f1e5')]:
 p=next(p for p in a['partitions']if p['name']==name);typ=a['partition_types'][p['type']];x,y=p['origin_um'];w,h=typ['outline_um'];ax.add_patch(Rectangle((x,y),w,h,fc=color,ec='#555'));ax.text(x+w/2,y+h/2,name,ha='center',fontsize=12)
x,y,w,h=9348.48,9616.32,574.56,738.72;ax.add_patch(Rectangle((x,y),w,h,fc='orange',ec='#a55'));ax.annotate('Actual selected r10 producer\nCatalogue geometry context only',xy=(x+w/2,y+h/2),xytext=(7800,11700),arrowprops={'arrowstyle':'->'},fontsize=9)
ax.plot([9348.48,1857.6,1857.6],[10355.04,10355.04,10385.28],c='#c43',lw=2,ls='--');ax.text(4200,10550,'2213 command+IO data bits\n≥7521.12 µm bbox distance\n≥19 links at405 µm; source has2 face stages',fontsize=9,color='#a32')
ax.text(0,7800,'Unplaced B113 obligations\n25 existing XO banks:5,106 FF\nNew L730 source banks:+2,304 FF\nNew transport:280I+6J FF\nProgramme:22,922 declared FF\n+44 native SRAMs; collar unknown\nTwo actual reset routes unpriced\nNo row or clock-budget reservation\nAbsolute existing-XO price unjoined',fontsize=8,color='#333')
ax.set_aspect('equal');ax.set_xlim(-400,13800);ax.set_ylim(5400,12500);ax.set_title('Selected logical producer/consumer across current planning context\nNo physical lane exists for these two UNPLANNED buses')
ax=axs[1];W,H=t['outline_um'];ax.add_patch(Rectangle((0,0),W,H,fc='white',ec='black'))
for c in t['hard_cores']:
 x,y=c['origin_um'];w,h=c['outline_um'];label=c['inst'].replace('u_sfucore_Q_','');color='#ddd'
 if label=='opstore_b':
  ax.add_patch(Rectangle((x,y),w,h,fc='none',ec='#777',ls='--'));h=483.84;color='#cfe4ff';label+=' compact proposal'
 ax.add_patch(Rectangle((x,y),w,h,fc=color,ec='#777'));ax.text(x+w/2,y+h/2,label,ha='center',fontsize=8)
for s in t['ft_slots']:
 pts=[p for b in s.get('bit_sites_um',[])for p in b];ax.scatter([p[0]for p in pts],[p[1]for p in pts],s=2,c='black')
for s in t['internal_stations']:
 ps=s.get('regs_um',[]);ax.scatter([p[0]for p in ps],[p[1]for p in ps],s=4,c='#999')
ax.add_patch(Rectangle((17.28,args.candidate_y),574.56,738.72,fc='#d2efce',ec='green',ls='--',lw=2));ax.text(304,400,f'Disabled true r10 location\ny={args.candidate_y} µm / 574.56 ×738.72\nExisting contacts checked separately\nInternal FF rows/clock/reset OPEN',ha='center',fontsize=8)
ax.text(25,805,'Joint collar+r10:279 CFG payload +5 status\nTwo reset routes separate / physically unpriced\nNo native physical stage count or view adopted',fontsize=8,color='#174e24');ax.set_aspect('equal');ax.set_xlim(-25,W+25);ax.set_ylim(-25,H+25);ax.set_title('Finite B113-local relocation alternative\nNominal free area does not prove actual placed-cell availability')
for ax in axs:ax.set_xlabel('x (µm)');ax.set_ylabel('y (µm)')
fig.suptitle('Source/geometry diagnosis only: exact SOURCE13 r10/collar identities; parent composite is pending, not as-built',fontsize=12);fig.tight_layout();fig.savefig(args.out,dpi=150)
