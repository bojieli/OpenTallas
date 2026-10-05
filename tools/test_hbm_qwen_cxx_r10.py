#!/usr/bin/env python3
"""Source/provenance/resource and synthetic frontend-copy controls; no compile."""
import contextlib,copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import prepare_hbm_qwen_cxx_r10 as P
import hbm_qwen_frontend_reuse_r10 as I
import run_hbm_qwen_cxx_r10 as R

class ColdSuccessor(unittest.TestCase):
 def test_actual_qualified_frontend_and_provenance(self):I.verify(False)
 def test_complete_census(self):
  m=I.load(P.OUT/'model.json');self.assertEqual(m['expected_archive_objects'],35684);self.assertEqual(m['observed_expected_objects'],18756);self.assertEqual(m['absent_expected_objects'],16928);self.assertEqual(len(I.entries()),35740)
 def test_priced_caps(self):
  m=I.load(P.OUT/'model.json');self.assertEqual(m['aggregate_output_bytes'],25*1024**3);self.assertEqual(m['per_file_bytes'],10*1024**3);self.assertLess(sum(m['output_components_bytes'].values()),m['aggregate_output_bytes']);self.assertEqual(m['CXX_limit_s'],3540);self.assertEqual(m['caps']['whole_wall_s'],3870)
 def test_unchanged_CXX_argv_no_frontend(self):
  p=P.review_prepare();old=I.load(P.OUT/'parent_checkpoint/proposal.json');self.assertEqual(p['commands']['Qwen'][1]['argv'],old['commands']['Qwen'][1]['argv']);self.assertEqual([x['phase']for x in p['commands']['Qwen']],['reuse_frontend','CXX']);self.assertIn('-B',p['commands']['Qwen'][1]['argv']);self.assertIn('-j16',p['commands']['Qwen'][1]['argv'])
 def test_root_guard(self):
  with patch.object(I,'ROOT',Path('/tmp/refused-root')):
   with self.assertRaisesRegex(ValueError,'source root changed'):I.verify()
 def fixture(self,root):
  old=root/'old/Qwen/obj';old.mkdir(parents=True);b=b'complete generated source';(old/'Vconnected.cpp').write_bytes(b);return root/'old',[dict(path='Qwen/obj/Vconnected.cpp',bytes=len(b),sha256=hashlib.sha256(b).hexdigest())]
 def test_exclusive_copy(self):
  with tempfile.TemporaryDirectory()as d:
   r=Path(d);old,kit=self.fixture(r);dest=r/'new';v=I.copy_kit(old,kit,dest);self.assertEqual(v['files'],1);self.assertFalse(v['objects_PCH_archive_binary_reused']);self.assertNotEqual((old/kit[0]['path']).stat().st_ino,(dest/'Vconnected.cpp').stat().st_ino)
   with self.assertRaises(ValueError):I.copy_kit(old,kit,dest)
 def test_no_partial_objects_or_PCH(self):
  with tempfile.TemporaryDirectory()as d:
   r=Path(d);old,kit=self.fixture(r);kit[0]['path']='Qwen/obj/old.o'
   with self.assertRaisesRegex(ValueError,'forbidden reused'):I.copy_kit(old,kit,r/'new')
 def test_copy_tamper_refused(self):
  with tempfile.TemporaryDirectory()as d:
   r=Path(d);old,kit=self.fixture(r);(old/kit[0]['path']).write_bytes(b'changed')
   with self.assertRaisesRegex(ValueError,'changed during'):I.copy_kit(old,kit,r/'new')
 def test_proposal_bytes_and_manifest_GO(self):
  p=P.review_prepare();path=P.OUT/'prepared_gate.json';self.assertEqual(path.read_bytes(),R.G.json_bytes(p));keys=['frame_sha256','resource_model_sha256','prior_terminal_verdict_sha256','prospective_headroom_sha256','frontend_manifest_sha256'];go=dict(schema=P.GO_SCHEMA,admitted=True,target='Qwen',source_commit='source',proposal_sha256=R.G.sha(path),runner_caps=P.RUNNER_CAPS,unit='q.service',output_path='/tmp/fresh-Q-r10',admission_record_path='results/new-Q-r10-GO.json',**{k:p[k]for k in keys});R.validate_go(go,path,'source')
  for k in keys+['proposal_sha256','source_commit']:
   bad=copy.deepcopy(go);bad[k]='wrong'
   with self.assertRaises(ValueError):R.validate_go(bad,path,'source')
 def test_exact_affinity_and_priced_fsize(self):
  info=dict(RuntimeMaxUSec='1h4min30s',LimitFSIZE=str(10*1024**3),OOMPolicy='stop');R.validate_limits('q.service','/q.service',str(96*1024**3),'0',range(8,24),info)
  with self.assertRaises(ValueError):R.validate_limits('q.service','/q.service',str(96*1024**3),'0',range(24),info)
 def test_mocked_reuse_then_cold_CXX_only(self):
  class Proc:
   pid=9999999;returncode=0
   def poll(self):return 0
  p=P.review_prepare();keys=['frame_sha256','resource_model_sha256','prior_terminal_verdict_sha256','prospective_headroom_sha256','frontend_manifest_sha256']
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);out=root/'output';proposal=root/'proposal.json';proposal.write_bytes(R.G.json_bytes(p));go=dict(schema=P.GO_SCHEMA,admitted=True,target='Qwen',source_commit='source',proposal_sha256=R.G.sha(proposal),runner_caps=P.RUNNER_CAPS,unit='q.service',output_path=str(out),admission_record_path='results/qGO.json',**{k:p[k]for k in keys});gp=root/'GO.json';gp.write_bytes(R.G.json_bytes(go));manifest=I.load(P.OUT/'frontend_manifest.json')
   def popen(cmd,**kwargs):
    if '--destination' in cmd:(out/'Qwen/reuse_frontend_receipt.json').write_text(json.dumps(dict(verdict='PASS_EXCLUSIVE_COMPLETE_QWEN_FRONTEND_ONLY',files=manifest['frontend_files'],bytes=manifest['frontend_bytes'],objects_PCH_archive_binary_reused=False)))
    if '--object-root' in cmd:(out/'Qwen/CXX_archive_receipt.json').write_text(json.dumps(dict(verdict='PASS_COLD_CXX_EXACT_THIN_ARCHIVE_ONLY')))
    return Proc()
   original_read=Path.read_text
   def read(path,*args,**kwargs):
    return 'MemAvailable: 134217728 kB\n' if path==Path('/proc/meminfo')else original_read(path,*args,**kwargs)
   with contextlib.ExitStack()as stack:
    stack.enter_context(patch.object(R.G,'git',side_effect=['source','GO','']))
    stack.enter_context(patch.object(R.subprocess,'check_output',return_value=gp.read_bytes()))
    stack.enter_context(patch.object(R.P,'prepare_target',return_value=p))
    stack.enter_context(patch.object(R,'validate_cgroup',return_value=dict(mocked=True)))
    stack.enter_context(patch.object(R.resource,'setrlimit'))
    stack.enter_context(patch.object(Path,'read_text',autospec=True,side_effect=read))
    calls=stack.enter_context(patch.object(R.subprocess,'Popen',side_effect=popen))
    R.execute(proposal,gp,'GO',out);self.assertEqual(calls.call_count,2)
   v=I.load(out/'verdict.json');self.assertEqual(v['verdict'],'PASS_NATIVE_QWEN_BUILD_ONLY');self.assertFalse(v['connected_measurement'])
if __name__=='__main__':unittest.main()
