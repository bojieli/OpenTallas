#!/usr/bin/env python3
"""Static/mock resource identity controls; never runs actual build/simulation."""
import contextlib,copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import prepare_hbm_rf_connected_calibration_r6 as P
import run_hbm_rf_connected_calibration_r6 as R
import hbm_ds_frontend_copy_r6 as I
class CalibrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.p=P.derive(json.loads(P.BASE.read_text()))
 def test_phase_budget(self):
  phases=list(R.commands(self.p,Path('/tmp/fresh'),'abc'));self.assertEqual(sum(x[2]for x in phases),4620);self.assertEqual(len(phases),8);self.assertEqual(P.RUNNER_CAPS['build_jobs'],16);self.assertEqual(self.p['caps']['whole_timeout_s'],4620)
 def test_make_jobs_and_flags(self):
  for target in ('DS','Qwen'):
   a=self.p['commands'][target][1]['argv'];self.assertIn('-j16',a);self.assertNotIn('-j4',a)
   for flag in ('-B','DEPS=','VM_USER_DIR=','OBJCACHE=','OPT_FAST=-O0','OPT_SLOW=-O0','OPT_GLOBAL=-O0'):self.assertIn(flag,a)
 def test_source_unchanged(self):self.assertEqual(self.p['source_sha256'],json.loads(P.BASE.read_text())['source_sha256'])
 def limits(self,cpus=None,mem=None):return R.validate_limits('a.service','/a.service',str(mem or 32*1024**3),'0',cpus or range(8,24),{'RuntimeMaxUSec':'77min','LimitFSIZE':str(1024**3),'OOMPolicy':'stop'})
 def test_equivalent_runtime_formats(self):
  for value in ('1h 17min','1h17min','77min','77min 0s','4620s','4620000ms','4620000000us','4620000000000ns','1h 16min 60s','4620.000000s'):
   with self.subTest(value=value):
    info={'RuntimeMaxUSec':value,'LimitFSIZE':str(1024**3),'OOMPolicy':'stop'}
    R.validate_limits('a.service','/a.service',str(32*1024**3),'0',range(8,24),info)
 def test_wrong_and_malformed_runtime_formats(self):
  for value in ('1h 16min','1h 18min','4620s 1us','4619.999999s','infinity','max','4620','-4620s','4620s garbage','4620seconds','',None):
   with self.subTest(value=value):
    info={'RuntimeMaxUSec':value,'LimitFSIZE':str(1024**3),'OOMPolicy':'stop'}
    with self.assertRaises(ValueError):R.validate_limits('a.service','/a.service',str(32*1024**3),'0',range(8,24),info)
 def test_affinity(self):self.assertFalse(self.limits()['cpu_quota_enforced'])
 def test_wrong_affinity(self):
  with self.assertRaises(ValueError):self.limits(range(24,28))
 def test_excess_memory(self):
  with self.assertRaises(ValueError):self.limits(mem=33*1024**3)
 def test_no_prediction(self):
  m=json.loads(P.MODEL.read_text());self.assertIsNone(m['resource_model']['completion_prediction']);self.assertIsNone(m['dependency_critical_path']['quantified_wall_s']);self.assertFalse(self.p['resource_plan']['CXX1800_is_expected_completion'])
 def test_no_failed_object_reuse(self):self.assertFalse(self.p['resource_plan']['partial_objects_reused']);self.assertEqual(self.p['commands']['DS'][0]['argv'][1],'tools/hbm_ds_frontend_copy_r6.py')
 def test_stale_copy_rejected(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d);(p/'bad.o').write_bytes(b'bad')
   with self.assertRaises(ValueError):I.files(p)
 def test_relocated_root_refused(self):
  manifest=json.loads(P.B.MANIFEST.read_text())
  manifest['source_root']='/tmp/refused-relocated-H1-root'
  with self.assertRaisesRegex(ValueError,'source root changed'):I.verify_inputs(manifest)
 def test_source_tamper_refused(self):
  b=json.loads(P.BASE.read_text());b['source_sha256'][next(iter(b['source_sha256']))]='0'*64
  with self.assertRaises(ValueError):P.derive(b)
 def test_failure_and_model_GO_binding(self):
  with tempfile.TemporaryDirectory()as d:
   path=Path(d)/'p.json';path.write_text(json.dumps(self.p));pin=self.p['reuse_inventory_pin']
   go=dict(schema=P.GO_SCHEMA,admitted=True,source_commit='source',proposal_sha256=R.G.sha(path),runner_caps=P.RUNNER_CAPS,output_path='/tmp/new-cold-campaign',unit='a.service',admission_record_path='results/new.json',reuse_inventory_sha256=pin['sha256'],**{k:pin[k]for k in ('prior_frontend_GO_commit','frontend_end_sha256','frontend_argv_sha256','frontend_source_bundle_sha256','frontend_tool_bundle_sha256')},**{k:self.p[k]for k in ('calibration_model_sha256','prior_failure_sha256')})
   R.validate_go(go,path,'source')
   for k in ('calibration_model_sha256','prior_failure_sha256','reuse_inventory_sha256'):
    bad=dict(go);bad[k]='0'*64
    with self.assertRaises(ValueError):R.validate_go(bad,path,'source')
 def go(self,path,output):
  p=json.loads(path.read_text());m=p['reuse_inventory_pin']
  return dict(schema=R.GO_SCHEMA,admitted=True,source_commit='source',proposal_sha256=R.G.sha(path),runner_caps=R.CAPS,unit='test.service',admission_record_path='results/newGO.json',reuse_inventory_sha256=m['sha256'],output_path=output,**{k:m[k]for k in ('prior_frontend_GO_commit','frontend_end_sha256','frontend_argv_sha256','frontend_source_bundle_sha256','frontend_tool_bundle_sha256')},**{k:p[k]for k in ('calibration_model_sha256','prior_failure_sha256')})
 def fake_run(self,fail=False):
  class Proc:
   pid=99999999;returncode=0
   def poll(self):return self.returncode
  with tempfile.TemporaryDirectory()as d:
   out=Path(d)/'new';path=Path(d)/'proposal.json';path.write_text(json.dumps(self.p));gopath=Path(d)/'GO.json';go=self.go(path,str(out));gopath.write_text(json.dumps(go));proposal=json.loads(path.read_text())
   def popen(cmd,**kwargs):
    proc=Proc()
    if '--copy' in cmd:
     if fail:proc.returncode=1;return proc
     dst=Path(cmd[cmd.index('--destination')+1]);dst.mkdir(parents=True)
     (dst.parent/'reuse_receipt.json').write_text(json.dumps({'verdict':'PASS_EXCLUSIVE_COMPLETE_FRONTEND_COPY_ONLY','inventory_sha256':go['reuse_inventory_sha256'],'files':11447}))
    if cmd[0].endswith('/Vconnected'):kwargs['stdout'].write(b'CONNECTED_RF_FENCE_PASS\nRESET_RF_FENCE_PASS\n')
    if '--out' in cmd:
     dst=Path(cmd[cmd.index('--out')+1]);q=0 if dst.parent.name=='DS' else 1
     dst.write_text(json.dumps({'verdict':'PASS_DIRECTED_CONNECTED_TRACE_ONLY','cases':[{'qwen':q}for _ in range(4)]}))
    return proc
   with contextlib.ExitStack()as stack:
    stack.enter_context(patch.object(R.G,'git',side_effect=['source','newGO','']))
    stack.enter_context(patch.object(R.subprocess,'check_output',return_value=gopath.read_bytes()))
    stack.enter_context(patch.object(R.P,'prepare',return_value=proposal))
    stack.enter_context(patch.object(R,'validate_cgroup',return_value={'mocked':True}))
    stack.enter_context(patch.object(R.resource,'setrlimit'))
    mock=stack.enter_context(patch.object(R.subprocess,'Popen',side_effect=popen))
    if fail:
     with self.assertRaises(RuntimeError):R.execute(path,gopath,'newGO',out)
     self.assertEqual(mock.call_count,1)
    else:R.execute(path,gopath,'newGO',out);self.assertEqual(mock.call_count,8)
   v=json.loads((out/'verdict.json').read_text());self.assertEqual(v['verdict'],'FAIL_INCOMPLETE'if fail else 'PASS_DIRECTED_NATIVE_DS_QWEN_CONNECTED_ONLY')
   self.assertTrue((out/'DS-reuse_frontend-end.json').exists())
   if not fail:
    for t,n,s,a in R.commands(proposal,out,'newGO'):self.assertTrue((out/f'progress-{t}-{n}.json').exists())
 def test_mocked_complete_reuse_and_Qwen_lifecycle(self):self.fake_run()
 def test_mocked_copy_failure_preserved_before_CXX(self):self.fake_run(True)
if __name__=='__main__':unittest.main()
