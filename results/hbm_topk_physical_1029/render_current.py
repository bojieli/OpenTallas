#!/usr/bin/env python3
import json
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
repo=Path(__file__).resolve().parents[2];q=Path(__file__).resolve().parent
src=Path('/srv/opentallas-scratch/claude/die-hbm-11/c25c_types_6658')
cm=json.load(open(src/'core_macros.json'))['cores']['ot_hbm_idx_topk_link_static']
m=json.load(open(repo/'results/hbm_topk_wpipe_1029/model_and_guides.json'))
sl=json.load(open(repo/'results/hbm_topk_wpipe_1029/slice.json'))
native=[25.92,207.36,69.12,243.0]
fig,ax=plt.subplots(figsize=(11,8))
ax.add_patch(Rectangle((0,0),650.16,500.04,fill=False,color='black'))
for mac in cm['macros']:
 x,y,x1,y1=mac['rect_um'];ax.add_patch(Rectangle((x,y),x1-x,y1-y,color='gray',alpha=.4));ax.text(x+5,y+35,mac['name'],fontsize=7)
for isl in sl['islands']:
 x,y,x1,y1=isl['rect_um'];ax.add_patch(Rectangle((x,y),x1-x,y1-y,color='red',alpha=.4))
boxes=[]
for g in m['new_register_guides']:
 x,y,x1,y1=g['rect_um'];boxes.append(g['rect_um']);color='tab:blue' if g['stage']==0 else 'tab:orange'
 ax.add_patch(Rectangle((x,y),x1-x,y1-y,color=color,alpha=.4));ax.text(x1+3,y+3,f"S{g['stage']} banks{g['banks']}",fontsize=7)
x,y,x1,y1=native;boxes.append(native);ax.add_patch(Rectangle((x,y),x1-x,y1-y,color='green',alpha=.5));ax.text(4,246,'existing native line_r',fontsize=7)
def overlap(a,b):return a[0]<b[2]-1e-6 and b[0]<a[2]-1e-6 and a[1]<b[3]-1e-6 and b[1]<a[3]-1e-6
assert all(not overlap(a,b) for i,a in enumerate(boxes) for b in boxes[i+1:]),'register-guide overlaps'
assert all(not overlap(a,mac['rect_um']) for a in boxes for mac in cm['macros']),'macro overlap'
assert all(not overlap(a,isl['rect_um']) for a in boxes for isl in sl['islands']),'island overlap'
ax.plot([.096]*2,[8.664,437.592],color='purple',lw=3,label='current selected_line W face,2368bits')
ax.set(xlim=(-5,660),ylim=(-5,510),aspect='equal',xlabel='local x (um)',ylabel='local y (um)',title='Current C25c TOPK WPIPE2 source/placement candidate\n8 actual 171.288x77.784 SRAMs; disjoint register guides; common-domain clock stage still held')
ax.legend(loc='upper right',fontsize=7)
fig.savefig(q/'current_guides.png',dpi=150,bbox_inches='tight')
(q/'guide_check.json').write_text(json.dumps(dict(register_boxes=9,register_overlap=0,macro_overlap=0,island_overlap=0,macro_size_um=[171.288,77.784],native_input_box_um=native,proof='rectangle geometry estimate only, actual mapped placement pending'),indent=2)+'\n')
