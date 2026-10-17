#!/usr/bin/env python3
"""Source-sized conservative Qwen ROMleaf parent candidate; no timing qualification."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/arch/qwen_romleaf_1552'
W,H=457.92,1166.4
LH,LW=110.16,172.8
slots=[(0,2),(0,1),(0,0),(1,2),(1,1),(1,0),(2,1),(2,0)]
xs=[100.116,199.908,329.832]
ys=[25.92,188.352,350.784] # M4/M6 common phase, unlike the old hand drawing.
children=[]
for i,(c,r) in enumerate(slots):
 children.append(dict(name=f'lsl{i}',at=[xs[c],ys[r]],size=[99.792,140.4],orient='MY' if c==0 else 'R0',clock=f'ck_lsl{i}'))
children.append(dict(name='node',at=[22.464,50.88],size=[47.52,432],orient='R0',clock='ck_node'))
for b in range(5):
 for p in range(2):
  children.append(dict(name=f'rom_p{p}_b{b}',at=[56.16+p*LW,511.488+b*130.464],size=[LW,LH],orient='R0' if p==0 else 'MY',clock=f'ck_rp{p*5+b}',clock_face='W' if p==0 else 'E'))
# Consumer regions replace the single ck fence. Final TX rung only, not every same-root FF.
regions={}
for i,(c,r) in enumerate(slots):
 x,y=xs[c],ys[r]
 if c==0:box=[75.6,y,94.5,y+140.4]
 elif c==1:box=[305.316,y,324.216,y+140.4]
 else:box=[435.24,y,455.76,y+140.4]
 regions[f'tx_final_{i}']=dict(box=box,selector=f'g_sl[{i}].g_hd.g_tx.g_r[1].u_tx',clock='ck',expected_ff=390,source='existing production second transmit rung',minimum_initial_capacity_um2=18.9*140.4)
for a in children:
 x,y=a['at'];w,h=a['size']
 assert min(x-2.16,y-2.16,W-2.16-x-w,H-2.16-y-h)>=20-1e-8,a
for i,a in enumerate(children):
 for b in children[i+1:]:
  ax,ay=a['at'];aw,ah=a['size'];bx,by=b['at'];bw,bh=b['size']
  dx=max(ax-bx-bw,bx-ax-aw);dy=max(ay-by-bh,by-ay-ah)
  assert dx>=-1e-8 or dy>=-1e-8,(a,b)
  # Existing bare-face E-W abutment: two leaf columns, first two LSL columns.
  abut=abs(dx)<1e-8 and dy<0 and a['orient']!=b['orient']
  assert abut or max(dx,dy)>=20-1e-8,(a,b,dx,dy)
model=dict(schema='opentallas.qwen.romleaf.structural_candidate.v1',status='CANDIDATE: parent physical glue/pins/CTS/GRT remain unmeasured',outline_um=[W,H],old_outline_um=[W,950.4],parent_area_delta_um2=W*(H-950.4),parent_area_ratio=H/950.4,leaf_outline_um=[LW,LH],leaf_ff=2233,leaf_macro_count=1,leaves_per_parent=10,replicas=768,total_leaf_instances=7680,ff_delta_per_parent=20,total_ff_delta=15360,added_cycles=0,macs_per_cycle='Parent unchanged: all 64 actual MAC lanes; leaf performs exact INT8->BF16 expansion for32 weights/cycle',rom_port_bytes_per_cycle=33.25,used_payload_bytes_per_cycle=32,leaf_input_bits_per_cycle=14,leaf_output_bits_per_cycle=512,leaf_nonclock_pins=527,leaf_total_pins=528,parent_active_payload_bits_per_cycle=1024,parent_raw_rom_leaf_bus_bits=5120,children=children,consumer_regions=regions,clock_delivery='phi-R per actual leaf/entry, no common phase; measured routed R and pair checks required',bandwidth_notes='Do not reuse prior 1024-bit gutter cut claim: all ten 512-bit physical leaf outputs and OR trees must be counted in actual all-incident cut extraction.',requirements=['Final TX rung grouped by consumer hierarchy, not by shared ck root. Remaining ck glue unfenced/global-placement before measured placement audit.','ROM request/control and reset stations require actual path and distance proof; this model does not assert closure.','Parent left five ROM clock entries W, right five E, aligned to actual leaf clk pin.','A1 bare-face macro-edge rule not used; existing20um macro-edge and child-channel rules retained.','Actual parent frame not production/adopted until all pins, pair clocks, CTS and route pass.'])
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'parent_plan.json').write_text(json.dumps(model,indent=2)+'\n')
print('PARENT_GEOMETRY_PASS',W,H,'area_ratio',H/950.4,'leaf_top',max(a['at'][1]+a['size'][1] for a in children))
if __name__=='__main__':
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 from matplotlib.patches import Rectangle
 fig,ax=plt.subplots(figsize=(7,13));ax.add_patch(Rectangle((0,0),W,H,fill=False))
 for a in children:
  x,y=a['at'];w,h=a['size'];ax.add_patch(Rectangle((x,y),w,h,fc='#edcf8a' if a['name'].startswith('rom') else '#c7d8ec',ec='black',lw=.7));ax.text(x+w/2,y+h/2,a['name']+'\n'+a['orient'],ha='center',va='center',fontsize=7)
 for n,r in regions.items():
  x,y,x1,y1=r['box'];ax.add_patch(Rectangle((x,y),x1-x,y1-y,fc='#90cb99',alpha=.7));ax.text((x+x1)/2,(y+y1)/2,n,rotation=90,ha='center',va='center',fontsize=5)
 ax.set_xlim(-10,W+10);ax.set_ylim(-10,H+10);ax.set_aspect('equal');ax.set_title('Conservative ROMleaf parent candidate\n457.92 x1166.4; exact pins/timing still pending');ax.set_xlabel('um');ax.set_ylabel('um');fig.tight_layout();fig.savefig(OUT/'parent_plan.png',dpi=130)
