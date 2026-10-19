#!/usr/bin/env python3
"""Separate actual PQ runtime op tags from configured idle/SENT state."""
from pathlib import Path
import argparse,hashlib,json,subprocess
from head_local_contract import ROOT,storage_offset
from cap_model import decode

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out)
 if out.exists():raise SystemExit('REFUSE_EXISTING_RUN_DIR')
 sources={}
 for n in ['rtl/v41die/ot_s81_cfg7_seq.sv','rtl/v41rom/ot_v41_elem_pq_tags.sv','rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_rt.sv']:
  s=subprocess.check_output(['git','show','ceaed19c4:'+n]);sources[n]=hashlib.sha256(s).hexdigest()
 epochs=[];checks=0
 for e in range(15):
  tag=e%4;rb=(tag<<14)+6144
  cfg=dict(obase=0,ops=0,np=0,fmt=2,rbase=rb,rcnt=828,rsplit=0,lo32=0,hi32=0)
  for dim in range(512):
   configured_row=6144+storage_offset(dim);assert configured_row<16384 and not configured_row&32768
   runtime_row=(tag<<14)|(configured_row&16383)
   full=runtime_row<<13|3<<8 # only tree node n=3, address model does not interpret partial math
   bad,leaf,port,word,_=decode(full,0,cfg);assert not bad
   badtagcfg=dict(cfg,rbase=(((tag+1)%4)<<14)+6144)
   assert decode(full,0,badtagcfg)[0]
   checks+=1
  epochs.append(dict(epoch=e,expected_broadcast_GO_count=e,conditional_actual_op_tag=tag,CAP_rbase=rb,
   actual_runtime_go_tag=None,actual_CFG_install_edge=None,
   release='after previous conflicting partial/decoder/CW/VP drain; before this epoch first actual return',
   configured_idle_is_separate=True))
 rec=dict(scope='ACTUAL SOURCE MODEL ONLY; runtime tag/CFG edge trace pending',source_ref='ceaed19c4',source_hashes=sources,
  actual_cfg_tag_rule='tag resets0; increments on every go_x broadcast before class gate; go_tag_c=tag',
  actual_element_rule='q_idle=r[15] from configured row; runtime q_row={otag[bk],r[13:0]}',
  configured_SENT_bit15='idle property of cfg, preserved; never converted into a real row',
  runtime_row_bits15_14='two-bit op tag0..3, all legal when actual source is non-idle',
  old_model_limit='head_local_contract.py retag_return/config reject flags2/3 and conflate runtime tag with configured SENT. Historical0/1 checks remain bounded; do not apply that restriction to these15 runtime epochs.',
  private_serializer='already preserves configured SENT and uses low14 real row6144+storage_offset; no serializer/data-path change required',
  per_epoch_CAP_CFG_required=True,epoch_contracts=epochs,address_and_wrong_tag_checks=checks,
  source_GO_delivery_all6_verified=False,actual_CFG_slot_port_lifetime=False,
  source_reader_retire_END_is_completion=False,native_phase=None,whole_token_deadline_pass=None,new_hardware=False)
 out.mkdir(parents=True);(out/'contract.json').write_text(json.dumps(rec,indent=2)+'\n')
 print('RUNTIME_TAG_SOURCE_MODEL_PASS epochs15 addresses7680 wrongtag7680; actualGO/CFGdrain/native OPEN')
if __name__=='__main__':main()
