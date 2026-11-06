import re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
base=Path(__file__).resolve().parent
fig,ax=plt.subplots(figsize=(11,9));ax.add_patch(Rectangle((0,0),650.16,535.68,fc='#eaf0de',ec='black'))
for n,x,y in re.findall(r'gm\\\[(\d)\\\].mem\} ot_sram_1r1w_64x512_m1_r2c2 ([\d.]+) ([\d.]+)',(base/'topk_original_macro_placement.tcl').read_text()):
 x,y=float(x),float(y);ax.add_patch(Rectangle((x,y),171.288,77.784,fc='#aab7c7',ec='black'));ax.text(x+85.644,y+38.892,'SRAM '+n+'\n512-bit bank',ha='center',va='center',fontsize=10)
ax.text(325.08,492,'Existing 8-bank geometry retained\nOpt-in eight local 3-bit fill column groups\nNo new edges; actual FF positions still owed',ha='center',va='center',fontsize=11)
ax.text(325.08,35,'SOURCE REVIEW: lockstep + mutants PASS; mapped24distinct local FFs\nNo physical release / clock or PG qualification claimed',ha='center',fontsize=10,color='#a22b26')
ax.set(xlim=(0,650.16),ylim=(0,535.68),aspect='equal',xlabel='x (um)',ylabel='y (um)',title='Topk fill-fanout source candidate on retained actual macro geometry')
fig.tight_layout();fig.savefig(base/'topk_fill_review.png',dpi=140)
