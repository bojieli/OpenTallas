#!/usr/bin/env python3
"""Opt-in endpoint-ordered160 successor; preserves prior failed raw images."""
import argparse,copy,hashlib,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from uarch_model_hcoll_rowgather import compile_calendar
from engram_compile import lower_local_slots,audit,FIELDS

def order_check(cal):
 for link in range(8):
  hs=[h for h in cal['hops'] if h['link']==link]
  for field in ['write','read','receive']:
   assert [h['seq'] for h in sorted(hs,key=lambda h:h[field])]==list(range(len(hs))),(link,field)

def compile_images(receipt,out):
 out.mkdir(parents=True,exist_ok=True);checks=[];baseline=None
 for layer in [1,14]:
  failed=compile_calendar(receipt,layer,two_rate=True,local_slots=True)
  try:order_check(failed)
  except AssertionError:pass
  else:raise AssertionError('historical nonmonotone sequence mutant escaped')
  cal=compile_calendar(receipt,layer,two_rate=True,local_slots=True,endpoint_ordered=True)
  order_check(cal);words,limit=lower_local_slots(cal);fieldaudit=audit(cal,words,True)
  assert limit==2091 and cal['done']==2495
  assert all(w==0 for code in words for w in code[2086:])
  signature=lambda c:([(h['link'],h['seq'],h['write'],h['read'],h['receive']) for h in c['hops']],c['requests'],c['consumer_reads'])
  # Presence/global-row metadata never changes the physical programme.
  for shift in range(8):
   other=copy.deepcopy(receipt);owners=[]
   for home,count in enumerate([4,4,4,4,3,2,2,1]):owners +=[(home+shift)%8]*count
   for row,home in zip([r for r in other['rows'] if r['layer']==layer],owners):row['rank']=(0 if layer==1 else 8)+home
   variant=compile_calendar(other,layer,two_rate=True,local_slots=True,endpoint_ordered=True)
   vwords,vlimit=lower_local_slots(variant);assert vwords==words and vlimit==limit
   checks.append(dict(layer=layer,shift=shift))
  d=out/f'layer{layer}';d.mkdir(exist_ok=True);images={}
  for n,code in enumerate(words):
   data=''.join(f'{w:064x}\n' for w in code).encode();(d/f'n{n}.hex').write_bytes(data);images[f'n{n}.hex']=hashlib.sha256(data).hexdigest()
  (d/'calendar.json').write_text(json.dumps(cal,indent=2)+'\n')
  manifest=dict(status='PRE_NATIVE_ENDPOINT_ORDERED160',target=120,native_profile='slot160_21_ordered_drain5',banks_per_node=21,capacity=2688,descriptor_guard=1346,base=0,limit=limit,loops=1,launch=399,first_control_consumer=406,issuer_done=2495,last_decoder_FF=2494,drain_control_indices=list(range(2086,2091)),images_sha256=images,field_audit=fieldaudit,physical_qualified=False,full96_release=False,normative_unchanged_programme=False)
  (d/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 report=dict(status='MODEL_PASS_NATIVE_GATE_OPEN',ownership_variants=checks,historical_sequence_order_mutant='rejected',endpoint_order_checks=['write','read','receive'],done=2495,limit=2091,finite_window_last_word=max((613*(h['ordinal']+1)+486)//487-1 for h in cal['hops']),source_sha256={str(p.relative_to(pathlib.Path(__file__).resolve().parents[2])):hashlib.sha256(p.read_bytes()).hexdigest() for p in [pathlib.Path(__file__).resolve(),pathlib.Path(__file__).resolve().parents[1]/'uarch_model_hcoll_rowgather.py',pathlib.Path(__file__).with_name('engram_compile.py')]})
 (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('receipt',type=pathlib.Path);p.add_argument('out',type=pathlib.Path);a=p.parse_args();compile_images(json.loads(a.receipt.read_text()),a.out)
