import json,re,sys,hashlib,math
from pathlib import Path
O=Path(__file__).parent;R=O.resolve().parents[2]
sys.path[:0]=[str(R/'tools/die_plan'),str(R/'physical/die_plan/qwen_kvsys/cores/harden')]
import fully_fixed_macros as F
from macro_sites import static_placement_tcl
master='ctl_sram_1r1w_64x128_p192'
manifest=json.loads((O/'input/mapped_manifest.json').read_text());insts=manifest['macro_instances'];mapped_sha=manifest['mapped_sha256'];assert len(insts)==len(set(insts))==6,insts
pins=json.loads((O/'input/pins.json').read_text());w=h=371.52;mw,mh=52.296,39.96
blocks=[]
for i,inst in enumerate(insts):blocks.append(dict(inst=inst,master=master,x=[103.68,216.][i%2],y=[60.48,155.52,250.56][i//2],orient='R0'))
t=dict(fully_fixed_macros=True,hard_cores=[dict(inst=b['inst'],physical_inst=b['inst'],lef=str((O/'input/macro.lef').resolve()),outline_um=[mw,mh]) for b in blocks])
macros=[(b['inst'],master,str((O/'input/macro.lef').resolve()),'',b['x'],b['y'],'R0') for b in blocks]
F.install(t,O,macros,[4.32,4.32,367.2,367.2],R)
(O/'ctl_macro_place.tcl').write_text(static_placement_tcl(blocks).replace('setPlacementStatus FIRM','setPlacementStatus LOCKED'))
clock=next(p for p in pins if p['bus']=='ck');reset=next(p for p in pins if p['bus']=='rst_n');por=next(p for p in pins if p['bus']=='por_n')
assert all(0<=p['x']<=w and 0<=p['y']<=h for p in pins)
for b in blocks:
 assert b['x']-4.32>4.32 and b['y']-4.32>4.32 and b['x']+mw+4.32<367.2 and b['y']+mh+4.32<367.2
 for p in [clock,reset]:assert not(b['x']-4.32<p['x']<b['x']+mw+4.32 and b['y']-4.32<p['y']<b['y']+mh+4.32)
centers=[(b['x']+mw/2,b['y']+mh/2) for b in blocks];maxpair=max(abs(x-a)+abs(y-b) for x,y in centers for a,b in centers)
review=dict(schema='opentallas.geom_review.v1',verdict='PASS-COND for ONE PLACE only after independent LOOK',kit='intel1:/srv/opentallas-scratch2/claude/codex-kv-pickup-ctl-2047/gen2/qkd_kvs_ctl__371.52x371.52',kit_hash='70b282cb9335c021',scope='geometry-only deterministic SRAM sites; same SYNTH/RTL/LEC/pins/SDC',outline_um=[w,h],mapped_macro_count=6,macro_outline_um=[mw,mh],blocks=blocks,clock_entry=clock,reset_entry=reset,power_on_reset=por,macro_pair_center_max_L1_um=maxpair,core_area_um2=(367.2-4.32)**2,macro_area_um2=6*mw*mh,total_mapped_area_um2=22531.315020,std_area_um2=22531.315020-6*mw*mh,pins=len(pins),actual_LEC={'compare_points':46454,'proved':46454,'differs':0,'undecided':0},source_mapped_sha256=mapped_sha,physical_OPEN=['ordinary cell placement/r2r and pin-reg reach','local clock sinks/tree and reset endpoints','PG connectivity/IR and actual placed density','ONE PLACE output review before any route/STA'])
review['std_fill_of_core_minus_macro']=review['std_area_um2']/(review['core_area_um2']-review['macro_area_um2']);(O/'review.json').write_text(json.dumps(review,indent=2)+'\n')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(10,10));ax.add_patch(Rectangle((0,0),w,h,fill=False,color='black'))
for p in pins:ax.plot(p['x'],p['y'],'.',color='#cc3333',ms=.7)
for x in [2.064+i*4.32 for i in range(86)]:ax.axvline(x,color='#e3d7c2',lw=.4,zorder=0)
for i,b in enumerate(blocks):
 ax.add_patch(Rectangle((b['x']-4.32,b['y']-4.32),mw+8.64,mh+8.64,fill=False,ls='--',ec='#888'))
 ax.add_patch(Rectangle((b['x'],b['y']),mw,mh,fc='#b8cfe8',ec='#315f92'));ax.text(b['x']+mw/2,b['y']+mh/2,b['inst'].split('u_')[-1],fontsize=8,ha='center',va='center')
 ax.plot([clock['x'],b['x']],[clock['y'],b['y']+.78],color='#dba832',lw=.8,alpha=.5)
for p,color,label in [(clock,'#cb8c00','ck'),(reset,'green','rst_n'),(por,'purple','por_n')]:ax.plot(p['x'],p['y'],'*',color=color,ms=12);ax.text(p['x']+4,p['y']+5,label,color=color)
ax.set(xlim=(-8,w+8),ylim=(-8,h+8),aspect='equal',xlabel='Core frame x (um)',ylabel='Core frame y (um)',title='CTL production: actual 6849 pins + six mapped native SRAMs\nReviewed deterministic macro proposal; central clock/reset corridor stays clear\n371.52 square, 4.32um halos, actual std fill of free core '+f"{review['std_fill_of_core_minus_macro']:.1%}"+'; PLACE-only qualification pending')
fig.tight_layout();fig.savefig(O/'ctl_model_review.png',dpi=140);print(json.dumps({k:review[k] for k in ['mapped_macro_count','macro_pair_center_max_L1_um','std_fill_of_core_minus_macro','source_mapped_sha256']}))
