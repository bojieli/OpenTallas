import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
FAKE='#!/bin/bash\necho "KVSLICE_BOOT $FAKE_V frames_sent 1/1"\nprintf "%s\\n" "$@" > argv\nif [ "$FAKE_RC" = 143 ]; then kill -TERM $$; fi\nexit "$FAKE_RC"\n'
class ExitStatus(unittest.TestCase):
 def _tree(self,p):
  for n in ('build/obj','image','vector','runs'):(p/n).mkdir(parents=True,exist_ok=True)
  (p/'image/epoch.txt').write_text('1\n')
  binary=p/'build/obj/Vtb_kvslice'; binary.write_text(FAKE); binary.chmod(0o755)
 def _run(self,p,name,rc,v):
  env=dict(os.environ,PRELOAD='0',FAKE_RC=str(rc),FAKE_V=v)
  return subprocess.run(['bash',str(HERE/'run_tok.sh'),str(p/'build'),str(p/'image'),str(p/'runs'),name,str(p/'vector')],env=env,capture_output=True,text=True)
 def test_preserves_failure_and_sigterm(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td); self._tree(p)
   for rc in (7,143):
    with self.subTest(rc=rc):
     r=self._run(p,str(rc),rc,'PASS')
     self.assertEqual(r.returncode,rc,r.stdout+r.stderr)
     self.assertEqual((p/'runs'/str(rc)/'exit').read_text().strip(),str(rc))
     self.assertIn(f'{rc} exit={rc}',r.stdout)
     self.assertIn('VERDICT FAIL',r.stdout)
 def test_exit0_is_not_a_pass(self):
  # TOK-QK-3 10-27: tok-qk-b48r4 exited 0 with KVSLICE_BOOT FAIL and was collected as "exit 0"; it must surface as FAIL.
  with tempfile.TemporaryDirectory() as td:
   p=Path(td); self._tree(p)
   for v,want,code in (('PASS','VERDICT PASS',0),('FAIL','VERDICT FAIL',3),('fake','VERDICT FAIL',3)):
    with self.subTest(v=v):
     r=self._run(p,'v'+v,0,v)
     self.assertEqual(r.returncode,code,r.stdout+r.stderr)
     self.assertIn(want,r.stdout)
     self.assertTrue((p/'runs'/('v'+v)/'verdict').read_text().startswith(want.split()[1]))
 def test_native_start_is_ordered_after_setup(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td); self._tree(p)
   (p/'build/native_boot.profile').write_text('1\n')
   r=self._run(p,'native',0,'PASS')
   self.assertEqual(r.returncode,0,r.stdout+r.stderr)
   self.assertIn('+START_AFTER_SETUP',(p/'runs/native/argv').read_text().splitlines())
 def test_layers_required(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td); self._tree(p)
   env=dict(os.environ,PRELOAD='0',FAKE_RC='0',FAKE_V='PASS',LAYERS='2')
   r=subprocess.run(['bash',str(HERE/'run_tok.sh'),str(p/'build'),str(p/'image'),str(p/'runs'),'L',str(p/'vector')],env=env,capture_output=True,text=True)
   self.assertEqual(r.returncode,3,r.stdout+r.stderr); self.assertIn('FAR_LAYER_SUMMARY missing',r.stdout)
 def test_infrastructure_failure_is_not_caught_mutant(self):
  import sys; sys.path.insert(0,str(HERE)); import kv_verdict
  with tempfile.TemporaryDirectory() as td:
   d=Path(td)
   self.assertEqual(kv_verdict.main([str(d),'--expect','fail']),1)
   (d/'sim.log').write_text('KVSLICE_BOOT FAIL errors 1\n')
   self.assertEqual(kv_verdict.main([str(d),'--expect','fail']),1)
   (d/'exit').write_text('137\n')
   self.assertEqual(kv_verdict.main([str(d),'--expect','fail']),1)
   (d/'sim.log').write_text('KVSLICE_BOOT PASS x\n')
   self.assertEqual(kv_verdict.main([str(d),'--expect','fail']),1)
   self.assertTrue((d/'verdict').read_text().startswith('FAIL'))
   (d/'exit').write_text('0\n')
   self.assertEqual(kv_verdict.main([str(d),'--layers','36','--expect','fail']),1)
   (d/'exit').write_text('134\n')
   (d/'sim.log').write_text('KVSLICE_BOOT FAIL errors 1\n')
   self.assertEqual(kv_verdict.main([str(d),'--expect','fail']),0)

 def test_mutant_classification(self):
  import sys; sys.path.insert(0,str(HERE)); import kv_verdict
  with tempfile.TemporaryDirectory() as td:
   d=Path(td); (d/'exit').write_text('0\n')
   (d/'sim.log').write_text('KVSLICE_BOOT FAIL frames_sent 839/7404 errors 3\n')
   self.assertEqual(kv_verdict.main([str(d),'--expect','fail']),0); self.assertTrue((d/'verdict').read_text().startswith('CAUGHT'))
   (d/'sim.log').write_text('KVSLICE_BOOT PASS frames_sent 7404/7404\n')
   self.assertEqual(kv_verdict.main([str(d),'--expect','fail']),1); self.assertTrue((d/'verdict').read_text().startswith('MUTANT_MISSED'))
   lines=''.join(f'FAR_LAYER_SUMMARY layer {n} ok 32 bad 0 cal_start 1 result_first 2 result_last 3 PASS\n' for n in range(36))
   (d/'sim.log').write_text('KVSLICE_BOOT PASS x\n'+lines.replace('layer 7 ok 32 bad 0 cal_start 1 result_first 2 result_last 3 PASS','layer 7 ok 31 bad 1 cal_start 1 result_first 2 result_last 3 FAIL'))
   self.assertEqual(kv_verdict.classify(d,36)[0],'FAIL')
   self.assertEqual(kv_verdict.main([str(d),'--layers','36','--expect','fail']),0)
   (d/'sim.log').write_text('KVSLICE_BOOT PASS x\n'+lines); self.assertEqual(kv_verdict.classify(d,36)[0],'PASS')
 def test_epoch_stall_cannot_catch_token_mutant(self):
  import sys; sys.path.insert(0,str(HERE)); import kv_verdict
  with tempfile.TemporaryDirectory() as td:
   d=Path(td); (d/'exit').write_text('0\n')
   stalled=''.join(f'FAR_LAYER_SUMMARY layer {n} ok 0 bad 0 cal_start -1 result_first -1 result_last -1 FAIL\n' for n in range(36))
   (d/'sim.log').write_text('KVSLICE_BOOT PASS frames_sent 7404/7404\n'+stalled)
   self.assertEqual(kv_verdict.main([str(d),'--layers','36','--expect','fail']),1)
   self.assertTrue((d/'verdict').read_text().startswith('FAIL'))
   (d/'sim.log').write_text('KVSLICE_BOOT FAIL errors 1\n'+stalled)
   self.assertEqual(kv_verdict.main([str(d),'--layers','36','--expect','fail']),1)
if __name__=='__main__':unittest.main()
