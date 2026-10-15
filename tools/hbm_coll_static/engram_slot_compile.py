#!/usr/bin/env python3
"""160-reservation typed kernel ->21 actual native256 catalogue banks/node.

Requires ot_hcoll_engram_chain_slot_node plus the actual local-slot producer.
This emits an opt-in component kernel, not unchanged normative G25A/HBM.
"""
import argparse,hashlib,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from uarch_model_hcoll_rowgather import compile_calendar
from engram_compile import lower_local_slots,audit,FIELDS

def compile_images(receipt,out):
 out.mkdir(parents=True,exist_ok=True)
 for layer in [1,14]:
  cal=compile_calendar(receipt,layer,two_rate=True,local_slots=True);words,limit=lower_local_slots(cal);checks=audit(cal,words,True)
  assert limit==2574 and len(words[0])==2688
  d=out/f'layer{layer}';d.mkdir(exist_ok=True)
  images={}
  for n,code in enumerate(words):
   data=''.join(f'{w:064x}\n' for w in code).encode();(d/f'n{n}.hex').write_bytes(data);images[f'n{n}.hex']=hashlib.sha256(data).hexdigest()
  r=dict(status='PRE_NATIVE_TYPED160_MACHINE_IMAGES',target=120,kernel='EngramlocalSlot160Drain5',native_profile='slot160_21_drain5',drain_NOPS=5,drain_control_indices=[2569,2570,2571,2572,2573],issuer_done_cycle=2978,source_module='ot_hcoll_engram_chain_slot_node',layer=layer,banks_per_node=21,nodes=9,limit=limit,launch=399,first_control_consumer=406,done=cal['done'],packets=160,logical_payloads=120,hops=720,application_NOPs=40,field_audit=checks,fields={k:dict(lsb=b,width=w) for k,(b,w) in FIELDS.items()},local_slot_fields=['srcrow','pkt_row','asm_row'],global_row_source='actual source descriptor metadata and native545 header; never catalogue constants',images_sha256=images,native_successor_proven=False,normative_unchanged_programme=False,physical_qualified=False)
  (d/'manifest.json').write_text(json.dumps(r,indent=2)+'\n');print(layer,limit,cal['done'],checks)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('receipt',type=pathlib.Path);p.add_argument('out',type=pathlib.Path);a=p.parse_args();compile_images(json.loads(a.receipt.read_text()),a.out)
