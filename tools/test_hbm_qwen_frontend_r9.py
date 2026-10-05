#!/usr/bin/env python3
"""Static admission/frame and mocked cold-build controls; no real compile."""
import contextlib,copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import prepare_hbm_qwen_frontend_r9 as P
import run_hbm_qwen_frontend_r9 as R

class QwenCalibration(unittest.TestCase):
 def test_actual_frame_provenance(self):P.verify_frame()
 def test_fullgeometry_unchanged_argv(self):
  p=P.prepare_target('Qwen');f=P.load(P.OUT/'frame.json')
  self.assertEqual(p['source_sha256'],f['source_sha256']);self.assertEqual(p['verified_toolchain'],f['verified_toolchain'])
  for a,b in zip(p['commands']['Qwen'],f['commands']['Qwen']):self.assertEqual(a['argv'],b['argv'])
  self.assertEqual([c['phase']for c in p['commands']['Qwen']],['frontend','CXX']);self.assertIn('-GQWEN=1',p['commands']['Qwen'][0]['argv']);self.assertFalse(p['DS_binary_reuse'])
 def test_unknown_completed_resource_bound(self):
  m=P.load(P.OUT/'model.json');self.assertIsNone(m['actual_completed_peak_bytes']);self.assertIsNone(m['actual_completion_time_s']);self.assertEqual(m['caps']['memory_bytes'],96*1024**3);self.assertEqual(m['phase_limits_s'],dict(frontend=1200,CXX=1800));self.assertEqual(m['caps']['whole_wall_s'],3030)
 def test_root_guard(self):
  with patch.object(P,'ROOT',Path('/tmp/refused-r9-root')):
   with self.assertRaisesRegex(ValueError,'execution root changed'):P.verify_frame()
 def test_changed_source_refused(self):
  real=P.sha
  with patch.object(P,'sha',side_effect=lambda path:'wrong'if str(path).endswith('ot_gpu_rf_service.sv')else real(path)):
   with self.assertRaisesRegex(ValueError,'source/tool changed'):P.verify_frame()
 def test_changed_compiler_refused(self):
  real=P.sha;tool=next(iter(P.load(P.OUT/'frame.json')['verified_toolchain']['files_sha256']))
  with patch.object(P,'sha',side_effect=lambda path:'wrong'if str(path)==tool else real(path)):
   with self.assertRaisesRegex(ValueError,'compiler identity changed'):P.verify_frame()
 def test_GO_binding_and_negative_pins(self):
  p=P.prepare_target('Qwen')
  with tempfile.TemporaryDirectory()as d:
   path=Path(d)/'proposal.json';path.write_bytes(R.G.json_bytes(p));go=dict(schema=P.GO_SCHEMA,admitted=True,target='Qwen',source_commit='source',proposal_sha256=R.G.sha(path),runner_caps=P.RUNNER_CAPS,unit='q.service',output_path='/tmp/new-Q-r9-output',admission_record_path='results/new-Q-r9-GO.json',**{k:p[k]for k in ['frame_sha256','resource_model_sha256','prior_oom_verdict_sha256','prospective_headroom_sha256']})
   R.validate_go(go,path,'source')
   for key in ['source_commit','proposal_sha256','frame_sha256','resource_model_sha256','prior_oom_verdict_sha256','prospective_headroom_sha256','target']:
    wrong=copy.deepcopy(go);wrong[key]='wrong'
    with self.assertRaises(ValueError):R.validate_go(wrong,path,'source')
 def test_kernel_affinity_and_memory_caps(self):
  info=dict(RuntimeMaxUSec='50min30s',LimitFSIZE=str(1024**3),OOMPolicy='stop')
  R.validate_limits('q.service','/q.service',str(96*1024**3),'0',range(8,24),info)
  for mem,swap,cpus in [('max','0',range(8,24)),(str(96*1024**3),'1',range(8,24)),(str(96*1024**3),'0',range(24))]:
   with self.assertRaises(ValueError):R.validate_limits('q.service','/q.service',mem,swap,cpus,info)
 def test_mocked_cold_build_lifecycle(self):
  class Proc:
   pid=9999999;returncode=0
   def poll(self):return 0
  p=P.prepare_target('Qwen')
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);out=root/'output';proposal=root/'proposal.json';proposal.write_bytes(R.G.json_bytes(p))
   go=dict(schema=P.GO_SCHEMA,admitted=True,target='Qwen',source_commit='source',proposal_sha256=R.G.sha(proposal),runner_caps=P.RUNNER_CAPS,unit='q.service',output_path=str(out),admission_record_path='results/qGO.json',**{k:p[k]for k in ['frame_sha256','resource_model_sha256','prior_oom_verdict_sha256','prospective_headroom_sha256']})
   gp=root/'GO.json';gp.write_bytes(R.G.json_bytes(go))
   def popen(cmd,**kwargs):
    if '--object-root' in cmd:(out/'Qwen/CXX_archive_receipt.json').write_text(json.dumps(dict(verdict='PASS_COLD_CXX_EXACT_THIN_ARCHIVE_ONLY')))
    return Proc()
   with contextlib.ExitStack()as stack:
    stack.enter_context(patch.object(R.G,'git',side_effect=['source','GO','']))
    stack.enter_context(patch.object(R.subprocess,'check_output',return_value=gp.read_bytes()))
    stack.enter_context(patch.object(R.P,'prepare_target',return_value=p))
    stack.enter_context(patch.object(R,'validate_cgroup',return_value=dict(mocked=True)))
    stack.enter_context(patch.object(R.resource,'setrlimit'))
    calls=stack.enter_context(patch.object(R.subprocess,'Popen',side_effect=popen))
    R.execute(proposal,gp,'GO',out);self.assertEqual(calls.call_count,2)
   v=P.load(out/'verdict.json');self.assertEqual(v['verdict'],'PASS_NATIVE_QWEN_BUILD_ONLY');self.assertFalse(v['connected_measurement']);self.assertTrue((out/'Qwen/frontend-memory.jsonl').exists());self.assertEqual(len(v['phases']),2)
 def test_stored_proposal_byte_parity(self):self.assertEqual((P.OUT/'prepared_gate.json').read_bytes(),R.G.json_bytes(P.prepare_target('Qwen')))
if __name__=='__main__':unittest.main()
