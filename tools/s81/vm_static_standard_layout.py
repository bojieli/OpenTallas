#!/usr/bin/env python3
"""Constructive 128-bank VM candidate respecting production20um macro margins.
Each slice places logical banks0..15 below and16..31 above its fixed transport;
each half has eight banks on either side. Actual pin/cut/clock and frontend
packing remain required. This grants the real standard bank leaf, not a parent
qualification based on component timing.
"""
import json,itertools
from pathlib import Path
import v19_pins_1014 as V
R=Path(__file__).resolve().parents[2]
def main():
 out=R/'physical/s81_die_pins/v20_vm_static_standard';out.mkdir(exist_ok=True)
 old=R/'physical/s81_die_pins/v20_vm_static/dsfd_vm_static_bank128.json';d=json.loads(old.read_text());pp={p:v['per_bit'] for p,v in d['ports'].items()}
 pp['ck']=[['N','M3',4.044,.084]];pp['rst_n']=[['N','M3',5.004,.084]]
 V.write(out,'dsfd_vm_static_bank128',[220.32,75.6],pp,'ck','W M4 requests, E M4 registered return/commit; production20um macro core-edge margin on all4sides; N M3 root/reset','v20_static_vm_standard',{'source':'tools/s81/vm_static_standard_layout.py','clock_entries':{'stream':['ck']},'reset_entries':{'stream':['rst_n']},'signal_layer_cap':'M4','pg_layer':'M5','parent_strap_layer':'M6','macro_margin_rule_um':20,'adoption':'standard native leaf CTS/TT/FF/DRC permitted; complete parent/phase/realcuts and frontend/staging remain OPEN'})
 nodes=[]
 for s in range(4):
  ox,oy=(656.64*(s%2),1753.92*(s//2))
  def add(name,master,x,y,w,h,**extra):nodes.append(dict(name=f'vm_s{s}_{name}',slice=s,master=master,xy_um=[round(ox+x,3),round(oy+y,3)],outline_um=[w,h],**extra))
  for b in range(32):
   x=64.8+285.12*((b%16)//8);y=(108 if b<16 else 1099.44)+77.76*(b%8)
   add(f'bank{b}','dsfd_vm_static_bank128',x,y,220.32,75.6,bank=b,clock_entry=f'ck_bank[{32*s+b}]')
  add('wscatter','dsfd_vm_static_scatter',144.72,730.08,345.6,103.68)
  add('read_frontend','dsfd_vm_static_suhc_fsr',144.72,835.92,345.6,51.84,qualification='outline provisional until final source area/cuts')
  add('return32','dsfd_vm_static_return',144.72,889.92,345.6,207.36,NROW=32)
  for h,y in enumerate([500.04,1150.2]):add(f'bridge{h}','dsfd_vm_static_relay128_b16',285.12,y,64.8,207.36,bank_range=[16*h,16*h+15])
  for q,(x,y) in enumerate([(0,365.04),(570.24,365.04),(0,1352.16),(570.24,1352.16)]):add(f'quarter{q}','dsfd_vm_static_relay128_b8',x,y,64.8,103.68,bank_range=[8*q,8*q+7])
 def overlap(a,b):
  x,y=a['xy_um'];w,h=a['outline_um'];xx,yy=b['xy_um'];ww,hh=b['outline_um']
  return x<xx+ww-1e-6 and x+w>xx+1e-6 and y<yy+hh-1e-6 and y+h>yy+1e-6
 bad=[(a['name'],b['name']) for a,b in itertools.combinations(nodes,2) if overlap(a,b)];assert not bad,bad
 for a in nodes:
  x,y=a['xy_um'];w,h=a['outline_um'];assert x>=0 and y>=0 and x+w<=1541.784 and y+h<=3952.776
 # Macro native dimensions and core margin, independent of parent geometry.
 mx=(220.32-174.12)/2;my=(75.6-29.736)/2
 assert min(mx-2.16,my-2.16)>=20
 report={'schema':'opentallas.s81.native_vm_standard_candidate.v1','status':'STANDARD_BANK_ASSIGNED_PARENT_CANDIDATE','parent_outline_um':[1541.784,3952.776],'bank_count':128,'macro_count':128,'bank_macro':'ot_sram_1r1w_512x128_m4_r2c2','macro_xy_local_um':[mx,my],'macro_core_edge_clearance_um':[mx-2.16,my-2.16],'nodes':nodes,'overlaps':bad,'outside':0,'slice_layout':'2x2 slices, logical bank halves lower/upper,8banks perphysicalcolumn perhalf','frontend_free_bands':{'top_xywh_um':[0,3481.92,1541.784,470.856],'east_xywh_um':[1291.68,0,250.104,3481.92]},'native_bank_pin_file':str((out/'dsfd_vm_static_bank128.tcl').relative_to(R)),'requirements':['actual frontend/68storage/dispatch packing','all per-bit relay/bank/scatter/return pin seams and cut<=0.60','measured independent native clocks/reset/epoch','uniform physical stage count and actual SRAM visibility','real compiler mapping and native arithmetic ownership'],'qualification':'no wholeVMfit/latency/timing claim;20um native bank needs no flow exception; previous47.52candidate is diagnostic only'}
 (out/'layout_candidate.json').write_text(json.dumps(report,indent=1)+'\n');print('STANDARD_VM_CANDIDATE',len(nodes),'rectangles128banks,0overlap/outside; margins',report['macro_core_edge_clearance_um'])
if __name__=='__main__':main()
