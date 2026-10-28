import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent));import canary as C
import os
os.environ['OT_CANARY_ANY_SOURCE']='1'  # tmp sources below are not flow-canary/sources snapshots

class Launch(unittest.TestCase):
 def test_client_is_independent_transient_service(self):
  with tempfile.TemporaryDirectory() as d:
   guard = Path(d)/"tools/die_plan/face_guard.py"
   guard.parent.mkdir(parents=True); guard.write_text("# pinned fixture\n")
   spec=dict(die='test',item='ref',top='top',mem_gb=16,kit='{gen}/ref',gen='true',run='true')
   a=SimpleNamespace(spec=None,die=['test'],src=d,root=str(Path(d)/'runs'),image='image',dry=False)
   with patch.object(C,'load_spec',return_value=({'test':spec},{})),patch.object(C,'git_head',return_value='abcdef123456'),patch.object(C.subprocess,'run',return_value=SimpleNamespace(returncode=0,stderr='')) as run:
    self.assertEqual(C.cmd_submit(a),0)
   cmd=run.call_args.args[0]
   self.assertEqual(cmd[:2],['systemd-run','--user']);self.assertIn('--property=Type=exec',cmd)
   self.assertIn('--property=KillMode=process',cmd);self.assertNotIn('nohup',' '.join(cmd))
   meta=json.loads(next((Path(d)/'runs').glob('*/canary_meta.json')).read_text())
   self.assertTrue(meta['client_unit'].startswith('flow-canary-test-'))
 def test_generated_physical_run_is_staged_without_live_git_dependencies(self):
  import subprocess
  with tempfile.TemporaryDirectory() as d:
   guard = Path(d)/"tools/die_plan/face_guard.py"
   guard.parent.mkdir(parents=True); guard.write_text("# pinned fixture\n")
   spec=dict(die='test',item='ref',top='top',mem_gb=16,kit='{gen}/ref',gen='mkdir -p {gen}/ref',run='bash {src}/physical/die_plan/qwen_kvsys/cores/harden/eco/hold_step.sh {kit} {src}')
   a=SimpleNamespace(spec=None,die=['test'],src=d,root=str(Path(d)/'runs'),image='image',dry=False)
   with patch.object(C,'load_spec',return_value=({'test':spec},{})),patch.object(C,'git_head',return_value='abcdef123456'),patch.object(C.subprocess,'run',return_value=SimpleNamespace(returncode=0,stderr='')) as launched:
    self.assertEqual(C.cmd_submit(a),0)
   cmd=launched.call_args.args[0][-1]
   run=next((Path(d)/'runs').iterdir())
   self.assertIn('--stage '+str(run/'gen'),cmd)
   self.assertIn('GENERATED',cmd)
   route=(run/'route.sh').read_text()
   self.assertIn(str(run/'gen/runtime_source'),route)
   self.assertNotIn(str(Path(d)/'physical/'),route)
   self.assertNotIn('hold_step.sh',(run/'job.sh').read_text())
   for text in (cmd,route,(run/'job.sh').read_text()):
    result=subprocess.run(['bash','-n'],input=text,text=True,capture_output=True)
    self.assertEqual(result.returncode,0,result.stderr)
 def test_service_failure_is_recorded_without_job_claim(self):
  with tempfile.TemporaryDirectory() as d:
   guard = Path(d)/"tools/die_plan/face_guard.py"
   guard.parent.mkdir(parents=True); guard.write_text("# pinned fixture\n")
   spec=dict(die='test',item='ref',top='top',mem_gb=16,kit='{gen}/ref',gen='true',run='true')
   a=SimpleNamespace(spec=None,die=['test'],src=d,root=str(Path(d)/'runs'),image='image',dry=False)
   with patch.object(C,'load_spec',return_value=({'test':spec},{})),patch.object(C,'git_head',return_value='abcdef123456'),patch.object(C.subprocess,'run',return_value=SimpleNamespace(returncode=1,stderr='bus unavailable')):
    self.assertEqual(C.cmd_submit(a),1)
   result=json.loads(next((Path(d)/'runs').glob('*/canary.json')).read_text())
   self.assertEqual(result['verdict'],'FAIL');self.assertEqual(result['failing'],['launch'])

class ImmutableSource(unittest.TestCase):
 def test_submit_refuses_mutable_worktree_source(self):
  # FLOW-SHARED-9: qwen_kvsys_core_167d3a11a ran from the lane worktree wt/qk-cores-6
  with tempfile.TemporaryDirectory() as d:
   spec=dict(die='test',item='ref',top='top',mem_gb=16,kit='{gen}/ref',gen='true',run='true')
   a=SimpleNamespace(spec=None,die=['test'],src=str(Path(d)/'wt/qk-cores-6'),root=str(Path(d)/'runs'),image='image',dry=False)
   with patch.dict(os.environ,{'OT_CANARY_ANY_SOURCE':''}),patch.object(C,'load_spec',return_value=({'test':spec},{})),patch.object(C.subprocess,'run') as run:
    self.assertEqual(C.cmd_submit(a),2)
   run.assert_not_called();self.assertFalse((Path(d)/'runs').exists())
 def test_trigger_and_gate_ignore_mutable_source_runs(self):
  spec=importlib.util.spec_from_file_location('trig9',Path(__file__).with_name('trigger.py'));T=importlib.util.module_from_spec(spec);spec.loader.exec_module(T)
  sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'autopilot'));import canary_gate as G
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)
   for name,src in (('wt_run','/srv/x/claude/wt/qk-cores-6'),('main_run','/srv/x/claude/flow-canary/sources/abbbffac9b85')):
    (root/name).mkdir();(root/name/'canary_meta.json').write_text(json.dumps({'spec':{'die':'qwen_kvsys_core'},'src':src,'src_commit':name,'client_unit':'u-'+name}))
   self.assertTrue(T.mutable_source({'src':'/srv/x/claude/wt/qk-cores-6'}));self.assertFalse(T.mutable_source({}))
   self.assertEqual(T.live_dies(root),{'qwen_kvsys_core'})
   (root/'main_run'/'canary.json').write_text('{}')
   self.assertEqual(T.live_dies(root),set())   # the live worktree run does not block the trigger
   self.assertEqual([r['src'] for r in G._runs(root,'qwen_kvsys_core')],['main_run'])

if __name__=='__main__':unittest.main()
