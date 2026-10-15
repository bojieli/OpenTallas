#!/usr/bin/env python3
"""Assign actual static 1R1W bank leaf inside existing VM column reservations.
Bank native build is authorized; parent transport packing and all simultaneous
client groups remain OPEN, never inferred from a standalone bank gate.
"""
import json,subprocess
from pathlib import Path
import v19_pins_1014 as V
R=Path(__file__).resolve().parents[2]
def main():
 out=R/'physical/s81_die_pins/v20_vm_static';out.mkdir(exist_ok=True)
 pp={};y=4.032
 for p,n in [('i_rv',1),('i_ra',9),('i_rt',8),('i_wv',1),('i_wa',9),('i_wd',128),('i_wm',4),('i_wt',8)]:
  pp[p]=[['W','M4',round(y+.096*i,3),.192] for i in range(n)];y+=.096*n+.96
 y=4.032
 for p,n in [('o_rv',1),('o_rd',128),('o_rt',8),('o_commit',1),('o_ca',9),('o_cm',4),('o_ct',8)]:
  pp[p]=[['E','M4',round(y+.096*i,3),.192] for i in range(n)];y+=.096*n+.96
 pp['ck']=[['N','M3',4.032,.192]];pp['rst_n']=[['N','M3',4.992,.192]]
 V.write(out,'dsfd_vm_static_bank128',[216.,47.52],pp,'ck','W independent read/write request capture, E actual registered data/commit observation, M3 root/reset; signal capM4', 'v20_static_vm_bank',{'source':'tools/s81/vm_static_bank_pins.py','reset_entries':{'stream':['rst_n']},'signal_layer_cap':'M4','adoption':'DIAGNOSTIC only:47.52 fails production20um macro margin; standard native grant is v20_vm_static_standard; no margin waiver'})
 leaves=[]
 for s in range(4):
  for b in range(32):
   y=108+49.68*b if b<16 else 1272.24+49.68*(b-16)
   leaves.append({'instance':f'bank_s{s}_b{b}','master':'dsfd_vm_static_bank128','at_vm_um':[388.8*s+64.8,y],'outline_um':[216.,47.52],'clock_entry':f'ck_bank[{32*s+b}]','domain':'stream_1p2'})
 # Pairwise legality of every reserved bank, independent of any source-only
 # area sum. Transport slots are not included in this bank-only qualification.
 for i,a in enumerate(leaves):
  ax,ay=a['at_vm_um']
  assert ax>=0 and ay>=0 and ax+216<=1520.064 and ay+47.52<=2108.16+1e-6
  for b in leaves[i+1:]:
   bx,by=b['at_vm_um'];assert not(ax<bx+216 and bx<ax+216 and ay<by+47.52-1e-6 and by<ay+47.52-1e-6)
 rec={'schema':'opentallas.s81.vm-static-bank-grant.v1','request':'777d025e8 wide_return_alternative, physical/s81_die_rtl/slot_change_requests/vm_static_v3.json','parent':'sp_vm existing1541.784x3952.776 die reservation','native_banks':leaves,'selected_geometry':{'bank_outline_um':[216.,47.52],'pitch_y_um':49.68,'central_transport':{'write_scatter':[0,902.88,345.6,103.68],'read_scatter':[0,1008.72,345.6,51.84],'return32':[0,1062.72,345.6,207.36]},'transport_status':'coordinates selected; pins, relays, cuts and actual same-latency path audit pending'},'bank_layer_cap':'M4, parentM5+ freed; do not reroute accepted legacybanks','native_transport_obligations':['exact static scatter and multiple return-group packing','real NROW32 return supports aggregate32rows/edge; complete native port allocation and bank release proof required','fixed3:4 serial client crossings and actual write visibility','fullrealfield address translation, gain/rowlayout and actual tensor ordering','signal cuts<=0.60, reach, phi-R, reset, GRT0+TT/FF+DRC0'],'qualification':'DIAGNOSTIC47.52_BANK_GEOMETRY_ONLY: production20um margin fails; native standard successor physical/s81_die_pins/v20_vm_static_standard'}
 (out/'bank_slots.json').write_text(json.dumps(rec,indent=1)+'\n')
 p=R/'results/arch/hier_contract_1011/s81.json';d=json.loads(p.read_text());d['sub_layouts']['sp_vm_static_v3_banks']={'source':'physical/s81_die_pins/v20_vm_static/bank_slots.json','qualification':'128actual1R1Wbankslotsassigned; wholeparenttransport remainsOPEN'};p.write_text(json.dumps(d,indent=1)+'\n')
 print('STATIC_VM_BANK128slots legal,0overlap,wholeparentOPEN')
if __name__=='__main__':main()
