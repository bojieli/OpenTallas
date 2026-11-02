from pathlib import Path
import json,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import geom_rules as G
R=Path(__file__).resolve().parent
old=G.Design('/srv/opentallas-scratch/claude/wt/codex-kv-physical-1101/results/kv_hroot_reloc_1131_A4_actual.tsv')
new=G.Design(R/'complete_model.tsv');rings=json.loads((R/'ring_footprint_proposal.json').read_text());cr=json.loads((R/'complete_clock_reset_manifest.json').read_text())
fig=plt.figure(figsize=(18,15));gs=fig.add_gridspec(3,2,height_ratios=[1,1,1.15]);axes=[fig.add_subplot(gs[0,:]),fig.add_subplot(gs[1,:]),fig.add_subplot(gs[2,0]),fig.add_subplot(gs[2,1])]
def view(ax,D,title,lim=None):
 c=[c for c in D.cells.values() if c[0]=='S'];xy=np.array([G.ctr(c) for c in c]);ax.scatter(xy[:,0],xy[:,1],s=.8,c='#285c87',alpha=.6)
 for p in D.pins:
  if p['sig']=='SIGNAL':ax.plot(p['x'],p['y'],'.',ms=1.2,color='#1b8b3b')
 clk=[p for p in D.pins if re.fullmatch(r'clk(?:_t\d+)?',p['name'])]
 ax.scatter([p['x'] for p in clk],[p['y'] for p in clk],marker='*',s=35,color='#edc642',edgecolor='#815100',linewidth=.3)
 ax.set(title=title,xlabel='um',ylabel='um',aspect='equal')
 ax.set_xlim(*(lim[:2] if lim else (0,1900.8)));ax.set_ylim(*(lim[2:] if lim else (0,838.08)))
view(axes[0],old,'Actual A4 post-DPL: pin p90 101.32 / max203.64; full graph1097.44um /348bad')
view(axes[1],new,'PREP real FF+fixed-object footprints: pin p9022.58 /max107.62; raw11reset FAIL retained\nConditional7-edge-qualified reset projection only:22408capture graph395.82um/0bad — parent boot/START join HELD')
for g in rings['groups']:
 a=g['reserved_rect'];axes[1].add_patch(Rectangle((a[0],a[1]),a[2]-a[0],a[3]-a[1],fill=False,edgecolor='#a05d38',lw=.5))
view(axes[2],new,'South actual bit-pin packing + SLG active window\nBand sizes retained; widest-drive FF spacing reserved',(880,1080,0,160))
view(axes[3],new,'East bit-keyed FF packing; same-size bands moved12.96um\nCore-clock candidate reach≤267.90; max1411sinks',(1790,1900.8,430,700))
for ax in axes[2:]:
 for g in rings['groups']:
  a=g['active_ff_rect'];ax.add_patch(Rectangle((a[0],a[1]),a[2]-a[0],a[3]-a[1],fill=False,edgecolor='#a05d38',lw=.8))
fig.suptitle('Hroot completeness proposal — source/ports/FF count/cycles unchanged; no ODB/CAD application\nAll22411 FF clock sources traced; forwarded-clock inputs preserved. Movable combinational cells still require normal GPL/DPL; no whole-cell/routing/timing qualification.',fontsize=13)
fig.tight_layout(rect=(0,0,1,.95));fig.savefig(R/'complete_model_review.png',dpi=150)
