import json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
p=Path(__file__).parent; out=p;out.mkdir(exist_ok=True)
iface=json.load(open(p/'port_interface.json'))['ports']; pub=json.load(open(p/'current_plan_output_pins.json')); W,H=244.56,514.08; X,Y=345.6,648
pins=[]
def add(n,b,d,f,x,y,l):pins.append(dict(name=n if b is None else f'{n}[{b}]',dir=d,face=f,x=round(x,3),y=round(y,3),layer=l))
def bus(n,w,d,f,start,pitch):
 for b in range(w):
  c=start+b*pitch
  x,y,l=(.042,c,'M4') if f=='W' else (W-.042,c,'M4') if f=='E' else (c,H-.048,'M5') if f=='N' else(c,.048,'M5')
  add(n,b if w>1 else None,d,f,x,y,l)
# Exact parent's source concatenation, payload bit 0 is busy. Epoch119 belongs to parent.
ctl=[]
for n,w in [('busy',1),('fault',1),('tok_idx',24),('tok_own',1),('tok_user',2),('tok_v',1),('tok_val',32),('w1_addr',24),('w1_data',32),('w1_we',1)]:
 for b in range(w):ctl.append((n,b if w>1 else None))
assert len(ctl)==119
public={(n,b):(x,y) for n,b,l,x,y,f in pub}
# Sort by exact target x to preserve correlation across the parent's paired pin layers.
for rank,b in enumerate(sorted(range(119),key=lambda b:public['x_ctl_o',b][0])):
 n,bit=ctl[b];add(n,bit,'out','N',.012+.192*rank,H-.048,'M5')
bus('dn_o',48,'out','W',242.796,.144)
bus('up_o',48,'out','E',.012,.048)
# Source groups occupy separate faces; no new data/control stages.
idx=0
for n,w in [('am_idx',24),('am_u',2),('am_v',1),('am_val',32),('sc_cfg',101)]:
 bus(n,w,'in','N',23.004+idx*1.344,1.344);idx+=w
bus('up_i',48,'in','W',260.028,.144)
bus('dn_i',48,'in','S',230.028,.144)
idx=0
for n,w in [('red_addr',24),('red_data',32),('red_we',1)]:
 bus(n,w,'in','S',90.012+idx*.288,.288);idx+=w
idx=0
for n,w in [('vm_we',8),('vm_win0',2),('vm_wdata0',32)]:
 bus(n,w,'in','E',450.012+idx*.288,.288);idx+=w
add('rst_n',None,'in','S',64.812,.048,'M5');add('ck',None,'in','C',122.268,257.04,'M5')
assert len(pins)==572 and len({z['name'] for z in pins})==572
expected={v['name'] if v['bits']==1 else f"{v['name']}[{b}]" for v in iface for b in range(v['bits'])};assert {z['name'] for z in pins}==expected
reach=[]
for z in pins:
 if z['dir']!='out':continue
 n=z['name'].split('[')[0]; bit=int(z['name'].split('[')[1][:-1]) if '[' in z['name'] else None
 if z['face']=='N':b=ctl.index((n,bit));pn='x_ctl_o'
 else:b=bit;pn='x_fw_o' if n=='dn_o' else 'x_fe_o'
 tx,ty=public[pn,b]; gx,gy=X+z['x'],Y+z['y'];reach.append(dict(child=z['name'],parent_payload=f'{pn}[{b}]',child_global_um=[gx,gy],public_plan_um=[tx,ty],L1_um=round(abs(gx-tx)+abs(gy-ty),3)))
assert max(z['L1_um'] for z in reach)<=405
pinobj=dict(schema='opentallas.core_pins.v1',module='qfd_dv_s5_sc2_leaf',outline_um=[W,H],pins=pins)
(out/'pins.json').write_text(json.dumps(pinobj,indent=2)+'\n')
spec=dict(name='qfd_dv_s5_sc2_leaf',top='qfd_dv_s5_sc2_leaf',kind='tile',sources=['rtl/qwen_dv/s5/qfd_dv_s5_sc2_leaf.sv','rtl/qwen_dv/s5/qfd_dv_s5_sc2_k79.sv','rtl/qwen_dv/s5/qfd_dv_s5_sc2_k79_helpers.sv'],params=dict(HARD_PINREG=1),clock_port='ck',reset_ports=['rst_n'],outline=dict(w=W,h=H),macros=[],route=dict(pd=.45),pins={f:sorted({z['name'].split('[')[0] for z in pins if z['face']==f}) for f in 'NEWS'})
(out/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
model=dict(scope='UNADOPTED child pin/source prototype. No P&R/clock/parent fold. No new cycles.',source_param='HARD_PINREG=1 explicit; native default0 must not be masked',standalone_mapped_cells=336662,source_mapped_guard='570/570 PASS',body_um=[X,Y,X+W,Y+H],outline_um=[W,H],signal_ceiling='M5; parent M6/M7 crossings reserved',public_pin_basis='Current committed plan_qc52.json sle_sc_v2 type_pins() generated records; source bit concatenation from825 strict bound RTL. These are plan pin centers, NOT measured boutFF locations.',output_plan_L1_max_um={f:max(r['L1_um'] for r in reach if next(z for z in pins if z['name']==r['child'])['face']==f) for f in 'NEW'},all_output_plan_legs_le405=True,actual_source_anchor_and_parent_timing='HELD: actual CA read, R8 final stages, bin/bout cell Q/D geometry, all same-depth reset and FT moves, parent clock loading still need source-correlated implementation. Output plan legs alone are not qualification.',clock='Legal M5 center-entry x122.268 y257.04, geometriccenter122.28. Structured tree TBD from actual placed sinks; no insertion-frame claim or CTS approval.',reach=reach)
(out/'model.json').write_text(json.dumps(model,indent=2)+'\n')
fig,axs=plt.subplots(1,2,figsize=(11,7));a=axs[0];a.add_patch(Rectangle((0,0),W,H,facecolor='#efefef',edgecolor='black'))
for f,c in [('N','royalblue'),('E','darkorange'),('W','green'),('S','crimson'),('C','purple')]:
 zz=[z for z in pins if z['face']==f];a.scatter([z['x'] for z in zz],[z['y'] for z in zz],s=8,c=c,label=f'{f}: {len(zz)} bits')
a.set_aspect('equal');a.set_xlim(-20,W+20);a.set_ylim(-20,H+20);a.legend(loc='center',fontsize=8);a.set_title('SC leaf candidate: 572 exact bits\nM4/M5 signals, center clock entry')
a=axs[1];a.add_patch(Rectangle((X,Y),W,H,facecolor='#eeeeee',edgecolor='black'));a.set_xlim(0,613.44);a.set_ylim(0,1339.2)
for r in reach:
 gx,gy=r['child_global_um'];tx,ty=r['public_plan_um'];a.plot([gx,tx],[gy,ty],color='steelblue',lw=.4,alpha=.4)
a.set_aspect('equal');a.set_title('215 source-correlated output plan legs\nN %.3f / E %.3f / W %.3f um'%tuple(model['output_plan_L1_max_um'][f] for f in 'NEW'));a.set_xlabel('parent x um');a.set_ylabel('parent y um')
fig.suptitle('PROPOSAL ONLY — actual native parent anchors/clock/reset/FT still HELD');fig.tight_layout();fig.savefig(out/'proposal.png',dpi=160)
print(json.dumps({k:v for k,v in model.items() if k!='reach'},indent=2))
