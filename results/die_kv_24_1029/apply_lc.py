#!/usr/bin/env python3
"""Preserve KV23's qualified LC bank/pin delta on a newly composed KV event."""
import json,shutil,sys,hashlib
from pathlib import Path
W=Path(sys.argv[1]).resolve();R=W/'results/die_kv_24_1029';S=R/(sys.argv[2] if len(sys.argv)>2 else 'event');D=R/(sys.argv[3] if len(sys.argv)>3 else 'event_lc');D.mkdir(exist_ok=True)
p=json.load(open(S/'plan.json'));n=0;c=0
for t in p['partition_types'].values():
 for x in t.get('contents',[]):
  if x['module']=='ot_qwen_tp8_pv_slice_t':x['module']='ot_qwen_tp8_pv_slice_lc_t';n+=1
 for h in t.get('hard_cores',[]):
  if h['module']=='kv3_pv_pair':
   fn='kv3_pv_pair_pins_'+('fMX_' if 'fMX' in h['pins_file'] else '')+'r26c_lc.json'
   f=W/'results/die_kv_23_1028/cores'/fn;assert f.is_file(),f
   b=f.read_bytes();dst=R/'cores'/fn;dst.write_bytes(b);h['pins_file']='../cores/'+fn;c+=1
p['note']=p.get('note','')+' | KV24 preserves qualified KV23 LC bank/pin delta512bankdefinitions/256paircoreslots,0cycles'
(D/'plan.json').write_text(json.dumps(p,indent=1)+'\n')
for f in ['sidecar.json','regions_ca.json','straps.json']:shutil.copyfile(S/f,D/f)
shutil.copytree(S/'latency',D/'latency',dirs_exist_ok=True)
assert n==512 and c==256,(n,c)
print('LCDELTA',n,c)
