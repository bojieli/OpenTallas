import ast,copy,gzip,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import qwen_kv_active_issuer as A
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.native=json.loads(gzip.decompress((A.BASE/'inputs/Qwen_tiled.json.gz').read_bytes()));cls.source=(ROOT/'tools/h3_qwen_bounded_native.py').read_text()
 def span(self,suffix):
  v=next(v['version']for v in self.native['operands']if v['version'].endswith(suffix));return A.spans(self.native,self.source,v,0,0)
 def test_decoded_active_spill(self):
  x=self.span('cacheK.16');self.assertEqual(x['active_words'],512);self.assertEqual(len(x['spans']),4);self.assertEqual([s['SM']for s in x['spans']],[0,0,1,1]);self.assertTrue(all(s['page'][0]=='HBM'for s in x['spans']));self.assertEqual(sum(s['sector32_count']for s in x['spans']),64)
 def test_active_scores_partial_RF(self):
  x=self.span('scores.18');self.assertEqual(x['shape'],[16,1]);self.assertEqual(x['spans'][0]['old_tail_bytes'],448);self.assertEqual(x['spans'][0]['physical_mirrors'],2)
 def test_exact_mapper_boundary_and_capacity(self):
  m,f=A.source_mapper(self.native,self.source);v=self.span('cacheK.16')['version'];self.assertEqual(f(m,v,8192,0)[0][2],0);self.assertEqual(f(m,v,8192,0)[1],0)
  with self.assertRaisesRegex(ValueError,'coordinate'):f(m,v,4194304,0)
 def test_position_and_home_mutants(self):
  with self.assertRaisesRegex(ValueError,'position'):A.spans(self.native,self.source,'unused',0,8192)
  n=copy.deepcopy(self.native);v=self.span('cacheK.16')['version'];value=next(x for x in n['operands']if x['version']==v);value['homes']=[h for h in value['homes']if h['SM']!=1]
  with self.assertRaisesRegex(ValueError,'coordinate'):A.spans(n,self.source,v,0,0)
 def receipts(self):
  data=bytes(range(32));o=dict(event='allocation_init_visible',sequence=4,generation=1,rank=0,address=32,valid=True,ready=True,full_sector_valid=True,payload_sha256=hashlib.sha256(data).hexdigest(),backend_source_sha256='1'*64,mask=0xffffffff);c=dict(o,event='old_sector_capture',sequence=5,origin_sequence=4);return o,c,data
 def test_positive_explicit_fixture_origins(self):
  o,c,p=self.receipts();self.assertTrue(A.verify_old_origin(o,c,p)['status'].startswith('PASS'))
  o['event']='backend_refill_capture';self.assertTrue(A.verify_old_origin(o,c,p)['status'].startswith('PASS'))
 def test_missing_origin_unknown(self):self.assertTrue(A.verify_old_origin(None,None,b'')['status'].startswith('UNKNOWN'))
 def test_origin_mutants(self):
  for field,value in [('generation',2),('address',64),('ready',False),('origin_sequence',3),('sequence',2),('payload_sha256','0'*64),('backend_source_sha256','2'*64),('full_sector_valid',False)]:
   with self.subTest(field=field):
    o,c,p=self.receipts();c[field]=value
    with self.assertRaises(ValueError):A.verify_old_origin(o,c,p)
  o,c,p=self.receipts();o['mask']=3
  with self.assertRaisesRegex(ValueError,'full-sector'):A.verify_old_origin(o,c,p)

 def test_all_groups_match_Popper_positive_span_plan(self):
  import h4_hbm_kv_validity_fence_model as P
  plan=P.compile_plan();active=A.prepare();self.assertEqual(len(active['groups']),72)
  for old,new in zip(plan['groups'],active['groups']):
   self.assertEqual(old['key'],new['key']);wanted={(s['version'],s['address'])for s in old['decoded_sectors']}
   got={(v['version'],s['byte_address']+offset)for v in new['active_operands']for s in v['spans']if s['page'][0]=='HBM'for offset in range(0,s['bytes'],32)}
   self.assertEqual(got,wanted)
   producer_versions={p['version']for p in old['producer_vectors']}
   got={(v['version'],s['provider_ref'],s['RF_slot'])for v in new['active_operands']if v['version']in producer_versions for s in v['spans']}
   self.assertEqual(got,{(s['version'],s['provider_ref'],s['RF_slot'])for s in old['producer_vectors']})
