"""Concurrent native formatter and literal request-loop checks; fixtures only."""
import pathlib,sys,tempfile,unittest,subprocess
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_observer_concurrency_probe as C
import qwen_rom_atomic_request_headers as H
from qwen_rom_source_observer_prepare import ROOT

class SerializedTests(unittest.TestCase):
 def test_all8192_concurrent_records(self):
  with tempfile.TemporaryDirectory() as td:
   r=C.probe(ROOT/'rtl/test/qwen_rom_runtime/observer/qwen_rom_observer_serialized_r1.hpp',pathlib.Path(td)/'probe')
   self.assertEqual(r['status'],'PASS_ALL8192_CONCURRENT_RECORDS');self.assertTrue(r['whole_atomic_headers_recovered']);self.assertFalse(r['DUT_or_provider_run'])
 def test_disabled_header_has_no_generated_dependency(self):
  with tempfile.TemporaryDirectory() as td:
   p=pathlib.Path(td)/'off.cpp';p.write_text('#include "'+str(ROOT/'rtl/test/qwen_rom_runtime/observer/qwen_rom_observer_serialized_r1.hpp')+'"\nint main(){}\n')
   subprocess.run(['g++','-std=c++20','-fsyntax-only',str(p)],check=True,capture_output=True)
 def profile(self):
  f={'wsrc':1,'tiles':1,'split':2,'k':4,'wbase':131072,'ts':128,'wcs':8,'ks':128,'jsh':2,'js':65536}
  r=[(10+j,0,g,131072+g*8+(j>>2)*65536) for j in range(8) for g in range(4)]
  return f,r
 def test_request_formula_fixture_scope(self):
  f,r=self.profile();v=H.request_profile(f,r,groups=4);self.assertEqual(v['word_requests'],32);self.assertFalse(v['response_payload_qualified']);self.assertFalse(v['effective_attention_mask_qualified'])
 def test_address_mutant_rejected(self):
  f,r=self.profile();r[0]=(10,0,0,131073)
  with self.assertRaisesRegex(ValueError,'source address'):H.request_profile(f,r,groups=4)
 def test_missing_port_rejected(self):
  f,r=self.profile()
  with self.assertRaisesRegex(ValueError,'all source loop'):H.request_profile(f,r[:-1],groups=4)
 def test_duplicate_port_rejected(self):
  f,r=self.profile();r[-1]=r[-2]
  with self.assertRaisesRegex(ValueError,'distinct source request'):H.request_profile(f,r,groups=4)
 def test_archived_failed_trace_recovers_only_headers(self):
  import gzip,json,hashlib
  d=ROOT/'results/uarch/qwen_rom_L0_observer_format_failure_20261003'
  receipt=json.loads((d/'original-native-concurrency-FAIL-r1.json').read_text())
  raw=gzip.decompress((d/'original-fixture.raw.gz').read_bytes())
  self.assertEqual(hashlib.sha256(raw).hexdigest(),receipt['raw_sha256'])
  self.assertEqual(receipt['status'],'FAIL_INTERLEAVED_CONCURRENT_RECORDS')
  headers=[tuple(map(int,m.groups())) for m in H.HEAD.finditer(raw)]
  want={(i,0,0,t,i%4,t*1024+i) for t in range(16) for i in range(512)}
  self.assertEqual(len(headers),8192);self.assertEqual(set(headers),want)
  self.assertGreater(receipt['malformed_lines'],0)
 def test_request_formula_multiple_chunks(self):
  f,r=self.profile();f['k']=8
  r+= [(18+j,0,g,131072+g*8+128+(j>>2)*65536) for j in range(8) for g in range(4)]
  self.assertEqual(H.request_profile(f,r,groups=4)['word_requests'],64)
 def test_handoff_has_no_provider_retirement_claim(self):
  import json
  d=ROOT/'results/uarch/qwen_rom_L0_observer_format_failure_20261003'
  r=json.loads((d/'Ampere-Russell-source-events-handoff-r1.json').read_text())
  self.assertFalse(r['calendar_gain_or_physical_adoption'])
  self.assertFalse(r['successor_formatter']['new_actual_relink_or_run_launched'])
  for event in r['events']:self.assertFalse(event['credit']);self.assertTrue(event['missing'])
 def test_actual_pinned_source_contract(self):
  c=H.source_contract();self.assertEqual(c['host_sha256'],'d42a775f630831d3f7640e1b439902f1d3ee07d1b92629375f090a5e4b93b6ad')

if __name__=='__main__':unittest.main()
