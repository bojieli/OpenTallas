import gzip
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import struct
import copy
import hashlib
import inspect
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from qwen_kv_observation_adapter import observed_storage
from qwen_kv_released_operator_gate import run as operator_run
sys.path.insert(0,'/home/ubuntu/OpenTallas-qwen-trained-native-execution/tools')
import h3_qwen_bounded_native as N
from qwen_kv_observation_verify import verify,assess,event_plan,verify_event_bindings,decoded_hashes
spec=importlib.util.spec_from_file_location('V',ROOT/'tools/qwen_native_terminal_coverage.py')
V=importlib.util.module_from_spec(spec);spec.loader.exec_module(V)
with gzip.open('/home/ubuntu/OpenTallas-qwen-trained-native-execution/results/uarch/h3_qwen_complete_native_20261002/tiled_r1/Qwen_tiled.json.gz','rt') as f:native=json.load(f)
class ObservationTests(unittest.TestCase):
 def test_disabled_identity(self):self.assertIs(observed_storage(N.BoundKVStorage,'unused'),N.BoundKVStorage)
 def test_missing_artifacts_unknown(self):
  with tempfile.TemporaryDirectory() as tmp:
   self.assertEqual(assess(native,tmp,V.verify_kv_journal)['status'],'UNKNOWN_MISSING_OBSERVATIONS')
 def test_event_plan_mutants(self):
  plan=event_plan(native)
  for mutation in ('duplicate','stale','reverse','missing','wrongversion','wrongrank'):
   rows=copy.deepcopy(plan)
   if mutation=='duplicate':rows[1]=copy.deepcopy(rows[0])
   elif mutation=='stale':rows[2]['key'][2]=1
   elif mutation=='reverse':rows[0],rows[1]=rows[1],rows[0]
   elif mutation=='missing':rows.pop()
   elif mutation=='wrongversion':rows[2]['writes']=[-1]
   elif mutation=='wrongrank':rows[0]['key'][1]^=1
   with self.subTest(mutation=mutation),self.assertRaises(ValueError):verify_event_bindings(native,rows)
 def test_operator_integration_no_decode(self):
  # Source/layout integration only; exact representable FP8 values, no checkpoint claim.
  from qwen_kv_observation_verify import payload_layout
  self.assertEqual(operator_run(None,None,None,None,None,None)['status'],'DISABLED_DEFAULT')
  with tempfile.TemporaryDirectory() as tmp:
   reference=Path(tmp)/'reference';reference.mkdir();inventory=[]
   for layer in range(36):
    for rank in range(2):
     key=(layer,rank,0);values={}
     for address,meta in payload_layout(native,key).items():values[address]=0 if meta['kind']=='K' else 56
     for kind,value in [('K',0.),('V',1.)]:np.save(reference/f'L{layer}.rank{rank}.{kind}.prepack.npy',np.full((4,128),value,np.float32),allow_pickle=False)
     data=b''.join(struct.pack('<QB',a,code)for a,code in sorted(values.items()));filename=f'L{layer}.rank{rank}.reference_U8.bin';(reference/filename).write_bytes(data)
     inventory.append(dict(key=key,file=filename,sha256=hashlib.sha256(data).hexdigest(),records=1024))
   (reference/'reference_inventory.json').write_text(json.dumps(inventory))
   files=[Path(N.__file__),Path(inspect.getfile(N.Storage)),Path(inspect.getfile(N.pack8)),Path(inspect.getfile(observed_storage)),Path(inspect.getfile(verify)),Path(inspect.getfile(operator_run))]
   admission=dict(source_file_sha256={str(f.resolve()):hashlib.sha256(f.read_bytes()).hexdigest()for f in files},native_sha256=hashlib.sha256((json.dumps(native,sort_keys=True,indent=2)+'\n').encode()).hexdigest(),reference_file_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in reference.iterdir()})
   result=operator_run(native,N,reference,Path(tmp)/'observation',admission,V.verify_kv_journal,enabled=True)
   self.assertEqual(result['independent_U8_numerical_comparison'],'PASS')
   self.assertEqual(result['actual_decoded_read_hash_binding'],'PASS')
   self.assertFalse(result['native_decode']);self.assertFalse(result['production_lifecycle_qualified'])
   admission['source_file_sha256'][str(Path(N.__file__).resolve())]='0'*64
   with self.assertRaisesRegex(ValueError,'source pin'):operator_run(native,N,reference,Path(tmp)/'bad',admission,V.verify_kv_journal,enabled=True)
 def test_real_storage_complete_lifecycle_and_bytes(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp)/'capture';m=observed_storage(N.BoundKVStorage,out,enabled=True,native=native)(native['source_program']);leases={}
   for op in native['operations']:
    m.pc=op['pc'];code=op['opcode'];a=op['attributes']
    if code=='KV_WRITE':
     key=(a['layer'],a['die']);tag=m.begin(*key,0);addresses=[]
     for kind in ('K','V'):
      base=N.extent(m.p,key[1],f'L{key[0]}.{kind}')['base']
      for head in range(4):
       for dim in range(128):addresses.append(base+(head*512*128+dim)*16 if kind=='K' else base+head*8192*128+dim)
     codes=(np.arange(1024,dtype=np.uint16)%127).astype(np.uint8);m.write(tag,addresses,codes);leases[key]=(tag,np.array(addresses))
    elif code=='KV_FENCE':
     key=(a['layer'],a['die']);tag,addresses=leases[key];leases[key]=(m.commit(tag),addresses)
    elif code=='KV_READ':
     key=(a['layer'],a['die']);fence,addresses=leases[key];lease=m.acquire(fence,*key,0);leases[key]=(lease,addresses)
     np.testing.assert_array_equal(m.read(lease,addresses),(np.arange(1024,dtype=np.uint16)%127).astype(np.uint8))
    elif code in ('SCORES','PV'):
     names={v['version']:v['name']for v in native['operands']};parts=names[op['reads'][1]].split('.');key=(int(parts[0][1:]),int(parts[1][1:]));m.done(leases[key][0],code)
   m.finish_observation();events=[json.loads(x)for x in(out/'kv_journal.jsonl').read_text().splitlines()]
   self.assertEqual(V.verify_kv_journal(native,events),432)
   result=verify(native,out,V.verify_kv_journal)
   self.assertEqual(result['events'],432)
   self.assertEqual(result['calendar']['write_address_sectors32'],19584)
   rows=[]
   for op in native['operations']:
    if op['opcode']=='KV_READ':rows.append(dict(pc=op['pc'],opcode='KV_READ',outputs=[dict(version=v,shape=[4,1,128],sha256=result['decoded_read_hashes'][v])for v in op['writes']]))
   self.assertEqual(verify(native,out,V.verify_kv_journal,read_trace=rows)['actual_decoded_read_hash_binding'],'PASS')
   bad=copy.deepcopy(rows);bad[0]['outputs'][0]['sha256']='0'*64
   with self.assertRaisesRegex(ValueError,'read-hash'):verify(native,out,V.verify_kv_journal,read_trace=bad)
   bad=copy.deepcopy(rows);bad[-1]=copy.deepcopy(bad[0])
   with self.assertRaisesRegex(ValueError,'unique72'):verify(native,out,V.verify_kv_journal,read_trace=bad)
   original_inventory=(out/'payload_inventory.jsonl').read_text()
   inventory=[json.loads(line)for line in original_inventory.splitlines()]
   inventory[0]['key'][1]^=1
   (out/'payload_inventory.jsonl').write_text(''.join(json.dumps(row)+'\n'for row in inventory))
   with self.assertRaises(ValueError):verify(native,out,V.verify_kv_journal)
   (out/'payload_inventory.jsonl').write_text(original_inventory)
   fixture={}
   data=(out/'committed_U8.bin').read_bytes()
   for record in map(json.loads,(out/'payload_inventory.jsonl').read_text().splitlines()):
    if record['file']=='committed_U8.bin':fixture[tuple(record['key'])]=dict(struct.iter_unpack('<QB',data[record['offset']:record['offset']+record['bytes']]))
   self.assertEqual(verify(native,out,V.verify_kv_journal,fixture)['independent_U8_numerical_comparison'],'PASS')
   bad_reference=copy.deepcopy(fixture);first=next(iter(bad_reference[0,0,0]));bad_reference[0,0,0][first]^=1
   with self.assertRaisesRegex(ValueError,'independent U8 numerical'):verify(native,out,V.verify_kv_journal,bad_reference)
   self.assertEqual(result['independent_U8_numerical_comparison'],'UNKNOWN_REFERENCE_NOT_SUPPLIED')
   raw=(out/'final_state_rank0.bin').read_bytes()
   bad=bytearray(raw);bad[36864]^=1;(out/'final_state_rank0.bin').write_bytes(bad)
   with self.assertRaisesRegex(ValueError,'retired state'):verify(native,out,V.verify_kv_journal)
   (out/'final_state_rank0.bin').write_bytes(raw)
   payload=(out/'final_U8.bin').read_bytes();bad=bytearray(payload);bad[8]^=1;(out/'final_U8.bin').write_bytes(bad)
   with self.assertRaisesRegex(ValueError,'payload identity'):verify(native,out,V.verify_kv_journal)
   (out/'final_U8.bin').write_bytes(payload)
   self.assertEqual((out/'committed_U8.bin').read_bytes(),(out/'final_U8.bin').read_bytes())
   self.assertEqual((out/'committed_U8.bin').stat().st_size,73728*9)
   with self.assertRaises(ValueError):m.begin(0,0,0)
   self.assertEqual(len((out/'kv_journal.jsonl').read_text().splitlines()),432)
