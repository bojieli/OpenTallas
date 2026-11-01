from pathlib import Path
import json,re
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
R=Path(__file__).resolve().parent;ROOT=R.parents[1]
pins=json.loads((ROOT/'physical/die_plan/qwen_kvsys/plan_of_record/pins/qkd_hr_phy_adp_pins_r26q9.json').read_text())['pins']
m='ot_sram_1r1w_512x128_m1_r2c2';sheet=json.loads((R/'views'/m/(m+'.json')).read_text());w=57.912;h=69.672
fig,axes=plt.subplots(1,2,figsize=(12,6),dpi=140)
for ax,(label,x) in zip(axes,[('A',25.92),('B',17.28)]):
 y=8.64;halo=4.32
 ax.add_patch(Rectangle((0,0),103.68,95.04,fill=False,ec='black',lw=1.2))
 ax.add_patch(Rectangle((x-halo,y-halo),w+2*halo,h+2*halo,fill=False,ec='#e07b00',ls='--',label='4.32um macro halo'))
 ax.add_patch(Rectangle((x,y),w,h,fc='#b7c5d4',ec='#35536f',alpha=.8))
 ax.text(x+w/2,y+h/2,'512x128 1R1W SRAM\nmux1 native aligned view\n57.912 x69.672um',ha='center',va='center',fontsize=8)
 ax.scatter([p['x'] for p in pins],[p['y'] for p in pins],s=2,c='#008b5b',label='560 unchanged core IO pins')
 ax.scatter([51.528],[94.944],s=80,c='red',marker='*',label='unchanged ck[0] entry')
 ax.set_title(f'Candidate {label}: macro origin({x},8.64)\n103.68x95.04 core unchanged; no added cycle',fontsize=10)
 ax.set_xlim(-8,111);ax.set_ylim(-8,103);ax.set_aspect('equal');ax.grid(alpha=.15);ax.set_xlabel('um');ax.set_ylabel('um')
 ax.legend(loc='lower right',fontsize=6)
fig.suptitle('PHY_adp disabled mux1 candidate: native SRAM, ordinary halo/channels, clock entry clear\nM4 macro power pins use existing M4→M5 macro grid; actual PDN/TT/FF gates still required',fontsize=10)
fig.tight_layout();fig.savefig(R/'fit.png')
