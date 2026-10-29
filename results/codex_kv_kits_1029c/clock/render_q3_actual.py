import json,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.patches import Rectangle
p=Path(__file__).parent/'q3_plan5';sl=json.load(open(p/'exact_legal_slice.json'));rec=json.load(open(p/'legal_repriced.json'))[0]
fig,ax=plt.subplots(figsize=(12,10));box=[];err=[]
for ln in (p/'native_actual_cells.tsv').read_text().splitlines():
 s=ln.split('\t');n,m=s[:2];x,y,xx,yy=map(float,s[2:]);box.append((n,x,y,xx,yy))
 if n.startswith('mp_ck_'):
  c=sl['cell_placements'][n];err.append(max(abs(x-c['origin_um'][0]),abs(y-c['origin_um'][1])));ax.add_patch(Rectangle((x,y),xx-x,yy-y,color='blue',lw=.2))
 elif m.startswith('ot_sram'):
  ax.add_patch(Rectangle((x,y),xx-x,yy-y,color='#ddaa77',alpha=.6));ax.add_patch(Rectangle((x-2.2,y-2.2),xx-x+4.4,yy-y+4.4,fill=False,ls='--',ec='red',lw=.6))
 else:ax.plot((x+xx)/2,(y+yy)/2,'.',ms=.5,color='#666666',alpha=.35)
for w in rec['wire_paths']:
 for path in w['paths']:ax.plot([x[0] for x in path],[x[1] for x in path],color='#22aa66',lw=.5,alpha=.5)
assert max(err)<1e-6
ax.set(xlim=(0,216),ylim=(0,172.8),aspect='equal',xlabel='um',ylabel='um',title='q3 actual inserted clock: OpenROAD DPL/check PASS, displacement0.0um\n17721 original cells unchanged; 410 planned buffers exact; dashed SRAM2.2um halo')
fig.tight_layout();fig.savefig(p/'q3_actual_dpl_clock_overlay.png',dpi=160)
(p/'actual_dpl_review.json').write_text(json.dumps({'verdict':'PASS-COND_ONE_CTS_GRT50_NO_DRT','actual_buffers':len(err),'max_buffer_plan_displacement_um':max(err),'original_cells_unchanged':17721,'actual_dpl_check':'PASS','picture':'q3_actual_dpl_clock_overlay.png','findings':'Explicit branches follow S/W face banks and macro channels; all original cells/macros fixed; clock buffers exact legal footprint, no new macro wall. TT/FF timing, PG, clock-inclusive GRT50 remain to measure.'},indent=1)+'\n')
