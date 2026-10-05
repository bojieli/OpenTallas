#!/usr/bin/env python3
"""Tiny native archive/link controls plus static proposal checks; no DUT build."""
import json,subprocess,tempfile,unittest
import run_hbm_rf_connected_thin_archive_r7 as R
from pathlib import Path
from unittest.mock import patch
import hbm_cxx_thin_archive_gate_r7 as W
import prepare_hbm_rf_connected_thin_archive_r7 as P

class ThinArchiveTests(unittest.TestCase):
 def fixture(self,root):
  (root/'Vconnected_classes.mk').write_text('VM_CLASSES_FAST += \\\n Vconnected__a \\\n Vconnected__b\n')
  (root/'a.cc').write_text('int value(){return 42;}\n')
  (root/'b.cc').write_text('extern int value(); int main(){return value();}\n')
  for src,name in [('a.cc','Vconnected__a.o'),('b.cc','Vconnected__b.o')]:
   subprocess.run(['/usr/bin/g++','-O0','-c',str(root/src),'-o',str(root/name)],check=True,capture_output=True)
  subprocess.run(['/usr/bin/ar','--thin','-rc',str(root/'Vconnected__ALL.a'),'Vconnected__a.o','Vconnected__b.o'],cwd=root,check=True,capture_output=True)
  subprocess.run(['/usr/bin/g++',str(root/'Vconnected__ALL.a'),'-o',str(root/'Vconnected')],check=True,capture_output=True)
 def test_thin_complete_and_standard_same_result(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);self.fixture(root);v=W.verify_archive(root);self.assertEqual(v['generated_objects'],2)
   subprocess.run(['/usr/bin/ar','-rc',str(root/'standard.a'),'Vconnected__a.o','Vconnected__b.o'],cwd=root,check=True,capture_output=True)
   subprocess.run(['/usr/bin/g++',str(root/'standard.a'),'-o',str(root/'standard')],check=True,capture_output=True)
   self.assertEqual(subprocess.run([str(root/'Vconnected')]).returncode,42);self.assertEqual(subprocess.run([str(root/'standard')]).returncode,42)
 def test_membership_missing_refused(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);self.fixture(root)
   with patch.object(W.subprocess,'check_output',return_value='Vconnected__a.o\n'):
    with self.assertRaisesRegex(ValueError,'membership incomplete'):W.verify_archive(root)
 def test_duplicate_members_refused(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);self.fixture(root)
   with patch.object(W.subprocess,'check_output',return_value='Vconnected__a.o\nVconnected__a.o\nVconnected__b.o\n'):
    with self.assertRaises(ValueError):W.verify_archive(root)
 def test_external_member_refused(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);self.fixture(root)
   with patch.object(W.subprocess,'check_output',return_value='/tmp/stale/Vconnected__a.o\n'):
    with self.assertRaisesRegex(ValueError,'escapes'):W.verify_archive(root)
 def test_standard_archive_refused(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);self.fixture(root);(root/'Vconnected__ALL.a').write_bytes(b'!<arch>\n')
   with self.assertRaisesRegex(ValueError,'thin archive required'):W.verify_archive(root)
 def test_make_failure_does_not_verify_or_retry(self):
  root=Path('/tmp/fresh/no-launch');argv=['/usr/bin/make','-C',str(root),'-B','AR=/usr/bin/ar --thin']
  with patch.object(W.subprocess,'call',return_value=2)as m,patch.object(W,'verify_archive')as v:
   with self.assertRaises(RuntimeError):W.execute(root,argv)
   self.assertEqual(m.call_count,1);v.assert_not_called()
 def test_cold_flags_required(self):
  with self.assertRaises(ValueError):W.execute(Path('/tmp/fresh'),['/usr/bin/make','-C','/tmp/fresh'])
 def test_proposal_caps_and_source_unchanged(self):
  base=json.loads(P.BASE.read_text());p=P.derive(base)
  self.assertEqual(p['source_sha256'],base['source_sha256']);self.assertEqual(p['runner_caps'],base['runner_caps']);self.assertEqual(p['runner_caps']['per_file_bytes'],1024**3)
  for t in ('DS','Qwen'):
   a=p['commands'][t][1]['argv'];self.assertIn('AR=/usr/bin/ar --thin',a);self.assertIn('-B',a);self.assertIn('-j16',a);self.assertIn('OPT_FAST=-O0',a);self.assertEqual(p['commands'][t][1]['timeout_s'],1800)
 def test_fresh_GO_must_bind_r2_failure(self):
  p=P.derive(json.loads(P.BASE.read_text()));pin=p['reuse_inventory_pin']
  with tempfile.TemporaryDirectory()as d:
   path=Path(d)/'proposal.json';path.write_text(json.dumps(p))
   go=dict(schema=P.GO_SCHEMA,admitted=True,source_commit='source',proposal_sha256=R.G.sha(path),runner_caps=P.RUNNER_CAPS,output_path='/tmp/fresh-thin-output',unit='test.service',admission_record_path='results/newGO.json',reuse_inventory_sha256=pin['sha256'],**{k:pin[k]for k in ('prior_frontend_GO_commit','frontend_end_sha256','frontend_argv_sha256','frontend_source_bundle_sha256','frontend_tool_bundle_sha256')},**{k:p[k]for k in ('calibration_model_sha256','prior_failure_sha256','prior_r2_failure_sha256')})
   R.validate_go(go,path,'source')
   go['prior_r2_failure_sha256']='0'*64
   with self.assertRaises(ValueError):R.validate_go(go,path,'source')

 def test_model_diagnosis_is_measured(self):
  d=json.loads(P.DIAG.read_text());self.assertEqual(d['signal25'],'SIGXFSZ');self.assertGreater(d['generated_object_bytes'],d['per_file_cap_bytes']);self.assertEqual(len(d['missing_generated_members']),4232)

if __name__=='__main__':unittest.main()
