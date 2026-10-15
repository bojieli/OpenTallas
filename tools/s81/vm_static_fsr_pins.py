#!/usr/bin/env python3
"""Native scheduled SU/HC/aux request frontend for the standard VM candidate."""
import json
from pathlib import Path
import v19_pins_1014 as V
R=Path(__file__).resolve().parents[2]
def main():
 out=R/'physical/s81_die_pins/v20_vm_static_standard';out.mkdir(exist_ok=True);pp={};x=40.044
 for p,n in [('i_v',18),('i_row',252),('i_slot',90),('i_group',3),('i_aux_v',12),('i_aux_row',168),('i_aux_slot',60)]:
  pp[p]=[['N','M5',round(x+.096*i,3),.084] for i in range(n)];x+=.096*n+.96
 for p,n,w,off in [('o_v',32,1,0),('o_addr',288,9,1),('o_tag',256,8,10)]:
  pp[p]=[]
  for i in range(n):
   b,k=divmod(i,w);pp[p].append(['S' if b<16 else 'N','M5',round(140.052+1.824*(b%16)+.096*(off+k),3),.084])
 pp['ck']=[['W','M4',4.032,.084]];pp['rst_n']=[['W','M4',4.992,.084]];pp['fault']=[['E','M4',4.032,.084]]
 V.write(out,'dsfd_vm_static_suhc_fsr',[345.6,51.84],pp,'ck','N fixed nativeSUHC and programmable auxiliary requests; S lower16/N upper16 bank metadata, aligned toward middle-gutter bridges','v20_vm_native_fsr',{'source':'tools/s81/vm_static_fsr_pins.py','clock_entries':{'stream':['ck']},'reset_entries':{'stream':['rst_n']},'signal_layer_cap':'M5','pg_layer':'M5','parent_strap_layer':'M6','adoption':'real source auxslot60 must match; native gate/pin timing and full standard parent/phase/compiled bank calendar remain OPEN'})
 report={'master':'dsfd_vm_static_suhc_fsr','outline_um':[345.6,51.84],'placements':'standard layout_candidate.json each vm_sN_read_frontend@(slice+144.72,slice+835.92)','port_bits':sum(len(v) for v in pp.values()),'source_request':'S_VM final i_aux_slot60 interface','interface_scope':'18native requests+12programmable auxiliary return-slot requests;32physical bank outputs','qualification':'not a claim that this fixed18+12 interface alone accepts20concurrentMIXreads; actual scheduler/profile must be implemented and proven'}
 (out/'fsr_receipt.json').write_text(json.dumps(report,indent=1)+'\n');print('NATIVE_FSR1182bits exactauxslot60 assigned')
if __name__=='__main__':main()
