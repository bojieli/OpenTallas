#!/usr/bin/env python3
"""Place each real pair of SU banks around its actual 1024-bit capture leaf."""
import json
from pathlib import Path
from residual_inventory import shelf
R=Path(__file__).resolve().parents[2]/'results/arch/qwen_vm_residual_1015/physical_inventory'
p=R/'inventory.json';x=json.loads(p.read_text());inv=x['inventory'];W=1188.;gap=40.;bw=371.52;bh=241.92;sw=86.4;sh=21.6
regions=[]
for r in range(8):
 boxes=[]
 def put(cls,n,px,py,o='R0'):
  v=inv[cls];boxes.append({'class':cls,'n':n,'region':r,'w':v['w'],'h':v['h'],'x':px,'y':py,'orient':o})
 for c in range(3):
  yy=c*(bh+gap);put('qvm_su_bank_native',c*2,0,yy);put('qvm_su_bank_native',c*2+1,bw+gap+sw+gap,yy,'MY');put('ot_qfd_vm_su1024_t',c,bw+gap,yy+(bh-sh)/2)
 y0=3*(bh+gap)
 for b in range(8):put('qvm_bank_banked_native',b,(b%3)*(bw+20),y0+(b//3)*(224.64+40))
 small=[]
 for b in x['alternatives']['regional_wide']['rectangles']:
  if b['region']==r and b['class'] not in ['qvm_su_bank_native','qvm_bank_banked_native','ot_qfd_vm_su1024_t']:small.append(b)
 start=2*bw+sw+3*gap #40um space right of mirrored bank
 little,h=shelf(small,W-start)
 assert h<=3*bh+2*gap
 for b in little:boxes.append(dict(b,x=start+b['x'],y=b['y']))
 HH=y0+2*(224.64+40)+224.64
 regions.append((boxes,HH))
H=max(h for _,h in regions);allboxes=[]
for r,(bs,h) in enumerate(regions):
 for b in bs:allboxes.append(dict(b,x=b['x']+(r%4)*(W+40),y=b['y']+(r//4)*(H+40)))
WW=4*W+120;HH=2*H+40
for i,a in enumerate(allboxes):
 for b in allboxes[i+1:]:assert min(a['x']+a['w'],b['x']+b['w'])<=max(a['x'],b['x']) or min(a['y']+a['h'],b['y']+b['h'])<=max(a['y'],b['y'])
assert len(allboxes)==487
x['alternatives']['regional_paired']={'outline_um':[WW,HH],'area_mm2':WW*HH/1e6,'region_outline_um':[W,H],'rectangles':allboxes,'channels_um':20,'native_SU_capture_motif_channels_um':40,'overlap':0,'outside':0,'qualification':'Source-connected bank-q/SU1024-sx motif only; remaining incident arcs, residual FFs, relays, clock/PG/cuts OPEN; no timing qualification'}
p.write_text(json.dumps(x,indent=2)+'\n');print(WW,HH)
