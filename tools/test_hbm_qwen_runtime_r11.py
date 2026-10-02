#!/usr/bin/env python3
"""Static qualification tests only; never execute the Qwen DUT."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import hbm_qwen_binary_reuse_r11 as I
import prepare_hbm_qwen_runtime_r11 as P
import run_hbm_qwen_runtime_r11 as R
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=P.review_prepare();cls.m=I.load(P.OUT/'model.json')
 def go(self,path):
  g=dict(schema=P.GO_SCHEMA,admitted=True,source_commit='test-source',proposal_sha256=I.sha(path),runner_caps=P.RUNNER_CAPS,target='Qwen',unit='r11-test.service',output_path='/tmp/r11-static-only',admission_record_path='results/rtl/r11/GO.json')
  for k in ('qualified_binary_manifest_sha256','resource_model_sha256','prior_terminal_verdict_sha256','prospective_headroom_sha256','parent_review_sha256'):g[k]=self.p[k]
  return g
 def test_actual_qualified_identity(self):
  m=I.verify(False);self.assertEqual(m['binary']['sha256'],'9536c0803d0fa712b3fda7669bdf91cb0b40ba88c91a226845bc8e94790ef44f');self.assertEqual(m['archive']['exact_members'],35684)
 def test_geometry(self):
  g=self.m['geometry'];self.assertEqual((g['NC'],g['SIMD_lanes'],g['dependent_SIMD_ops']),(16,128,2056));self.assertEqual(g['rows'],[16,16,4096,4096]);self.assertTrue(g['reset_stale_epoch_case'])
 def test_caps_price(self):
  self.assertEqual(sum(self.m['phases'].values()),self.m['caps']['whole_wall_s']);self.assertEqual(self.m['simulation_cap_s'],67560);self.assertIsNone(self.m['Qwen_actual_runtime_throughput']);self.assertEqual(self.m['caps']['cpus'],[0]);self.assertEqual(self.m['caps']['memory_bytes'],32*1024**3)
 def test_commands_no_build(self):
  c=self.p['commands']['Qwen'];self.assertEqual([x['phase']for x in c],['reuse_binary','simulation','trace']);self.assertEqual(c[1]['argv'],['/usr/bin/stdbuf','-oL','-eL','<fresh-output>/Qwen/obj/Vconnected']);self.assertNotIn('make',json.dumps(c));self.assertNotIn('verilator',json.dumps(c))
 def test_root_relocation_rejected(self):
  with patch.object(I,'ROOT',Path('/tmp/relocated')):
   with self.assertRaisesRegex(ValueError,'source root'):I.verify(True)
 def test_exclusive_copy(self):
  with tempfile.TemporaryDirectory()as d:
   s=Path(d)/'source';s.write_bytes(b'\x7fELFexact-test');m={'binary':dict(path=str(s),bytes=s.stat().st_size,sha256=I.sha(s),mode=0o755)};dst=Path(d)/'new/elf';v=I.copy_binary(m,dst);self.assertFalse(v['objects_PCH_archive_reused']);self.assertEqual(dst.read_bytes(),s.read_bytes());self.assertNotEqual(s.stat().st_ino,dst.stat().st_ino)
   with self.assertRaises(ValueError):I.copy_binary(m,dst)
 def test_copy_tamper_rejected(self):
  with tempfile.TemporaryDirectory()as d:
   s=Path(d)/'source';s.write_bytes(b'\x7fELFbad');m={'binary':dict(path=str(s),bytes=s.stat().st_size,sha256='0'*64,mode=0o755)}
   with self.assertRaisesRegex(ValueError,'hash mismatch'):I.copy_binary(m,Path(d)/'dest')
 def test_go_valid_and_pins(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d)/'p.json';p.write_bytes(R.G.json_bytes(self.p));g=self.go(p);R.validate_go(g,p,'test-source')
   for k in ('qualified_binary_manifest_sha256','resource_model_sha256','parent_review_sha256','source_commit','proposal_sha256'):
    bad=copy.deepcopy(g);bad[k]='changed'
    with self.assertRaises(ValueError):R.validate_go(bad,p,'test-source')
 def test_hard_affinity_no_cpuquota(self):
  info=dict(RuntimeMaxUSec='18h 51min 30s',LimitFSIZE=str(P.RUNNER_CAPS['per_file_bytes']),OOMPolicy='stop');v=R.validate_limits('test.service','/user/test.service',str(32*1024**3),'0',{0},info);self.assertFalse(v['cpu_quota_enforced'])
  with self.assertRaises(ValueError):R.validate_limits('test.service','/user/test.service',str(32*1024**3),'0',{0,1},info)
 def test_duration_exact(self):
  self.assertEqual(R.duration_seconds('18h 51min 30s'),67890)
  with self.assertRaises(ValueError):R.duration_seconds('67890unknown')
 def test_prepared_bytes(self):
  if (P.OUT/'prepared_gate.json').exists():self.assertEqual((P.OUT/'prepared_gate.json').read_bytes(),R.G.json_bytes(self.p))
 def test_failure_receipt_preserved(self):
  with tempfile.TemporaryDirectory()as d:
   base=Path(d);p=base/'p.json';p.write_bytes(R.G.json_bytes(self.p));g=self.go(p);g['output_path']=str(base/'output');gp=base/'GO.json';gp.write_bytes(R.G.json_bytes(g))
   def git(*args):return 'test-source' if args[0]=='rev-parse' else ''
   with patch.object(R.G,'git',side_effect=git),patch.object(R.subprocess,'check_output',return_value=gp.read_bytes()),patch.object(P,'prepare_target',side_effect=ValueError('STATIC_INJECTED_PREPARE_FAILURE')):
    with self.assertRaisesRegex(RuntimeError,'STATIC_INJECTED'):R.execute(p,gp,'test-GO',base/'output')
   v=I.load(base/'output/verdict.json');self.assertEqual(v['verdict'],'FAIL_INCOMPLETE');self.assertEqual(v['phases'],[]);self.assertFalse(v['connected_measurement']);self.assertEqual((base/'output/proposal.json').read_bytes(),p.read_bytes())
   with self.assertRaises(ValueError):R.execute(p,gp,'test-GO',base/'output')
 def test_source_pin_tamper_rejected(self):
  m=I.load(P.OUT/'qualified_binary.json');m['source_sha256']=dict(m['source_sha256']);f=next(iter(m['source_sha256']));m['source_sha256'][f]='0'*64
  original=I.load
  with patch.object(I,'load',side_effect=lambda p:m if Path(p).name=='qualified_binary.json' else original(p)):
   with self.assertRaisesRegex(ValueError,'source/tool changed'):I.verify(False)
 def test_pinned_buffering_and_trace_tools(self):
  for f,h in self.p['runtime_libraries_sha256'].items():self.assertEqual(I.sha(f),h)
  self.assertEqual(self.p['gate_tool_sha256']['tools/check_hbm_rf_connected_trace.py'],I.sha(I.ROOT/'tools/check_hbm_rf_connected_trace.py'))
if __name__=='__main__':unittest.main()
