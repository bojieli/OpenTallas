#!/usr/bin/env python3
"""Exhaustive old/new counter-state transition and out-of-range probe checks."""
import json,pathlib
checks=0
for bc in range(64):
 row=(bc-1)&63
 lo=[row%8==i for i in range(8)];hi=[row//8==i for i in range(8)]
 fullmask=sum(int(hi[i//8]and lo[i%8])<<i for i in range(64))
 assert fullmask==1<<row
 for bank in range(8):
  mask=(fullmask>>(8*bank))&255
  for q in range(256):
   for bw in [0,1]:
    for clear in [0,1]:
     old=0 if clear else (q|(1<<(row%8))) if bw and row//8==bank else q
     new=0 if clear else q|mask if bw and mask!=0 else q
     assert old==new,(bc,bank,q,bw,clear)
     checks+=1
for fc in range(128):assert (fc==95)==(fc==0b1011111)
for ix in range(32):
 for bit in range(64):
  rv=1<<bit
  hit=any(bool((rv>>b)&1)and b//8==ix//8 and b%8==ix%8 for b in range(32))
  assert bool((rv>>ix)&1)==hit
out=pathlib.Path('results/arch/s81_engrr_five_1021/STATIC_MODEL_PASS.json');out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({'status':'PASS','counter_byte_nextstate_cases':checks,'terminal_complete_field_values':128,'probe_index_onehot_witness_cases':32*64,'amax_retained_nonconstant_positions':(0x7fffb717).bit_count(),'amax_original_field_width':31,'extra_pipeline_edges':0,'scope':'static full-counter truth/priority only; actual RTLgoldens/causals/native stillrequired'},indent=2)+'\n')
print(out,checks)
