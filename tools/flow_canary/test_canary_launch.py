import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).parent));import canary as C

class Launch(unittest.TestCase):
 def test_client_is_independent_transient_service(self):
  with tempfile.TemporaryDirectory() as d:
   spec=dict(die='test',item='ref',top='top',mem_gb=16,kit='{gen}/ref',gen='true',run='true')
   a=SimpleNamespace(spec=None,die=['test'],src=d,root=str(Path(d)/'runs'),image='image',dry=False)
   with patch.object(C,'load_spec',return_value=({'test':spec},{})),patch.object(C,'git_head',return_value='abcdef123456'),patch.object(C.subprocess,'run',return_value=SimpleNamespace(returncode=0,stderr='')) as run:
    self.assertEqual(C.cmd_submit(a),0)
   cmd=run.call_args.args[0]
   self.assertEqual(cmd[:2],['systemd-run','--user']);self.assertIn('--property=Type=exec',cmd)
   self.assertIn('--property=KillMode=process',cmd);self.assertNotIn('nohup',' '.join(cmd))
   meta=json.loads(next((Path(d)/'runs').glob('*/canary_meta.json')).read_text())
   self.assertTrue(meta['client_unit'].startswith('flow-canary-test-'))
 def test_service_failure_is_recorded_without_job_claim(self):
  with tempfile.TemporaryDirectory() as d:
   spec=dict(die='test',item='ref',top='top',mem_gb=16,kit='{gen}/ref',gen='true',run='true')
   a=SimpleNamespace(spec=None,die=['test'],src=d,root=str(Path(d)/'runs'),image='image',dry=False)
   with patch.object(C,'load_spec',return_value=({'test':spec},{})),patch.object(C,'git_head',return_value='abcdef123456'),patch.object(C.subprocess,'run',return_value=SimpleNamespace(returncode=1,stderr='bus unavailable')):
    self.assertEqual(C.cmd_submit(a),1)
   result=json.loads(next((Path(d)/'runs').glob('*/canary.json')).read_text())
   self.assertEqual(result['verdict'],'FAIL');self.assertEqual(result['failing'],['launch'])

if __name__=='__main__':unittest.main()
