import os
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
class ExitStatus(unittest.TestCase):
 def test_preserves_success_failure_and_sigterm(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)
   for n in ('build/obj','image','vector','runs'):(p/n).mkdir(parents=True)
   (p/'image/epoch.txt').write_text('1\n')
   binary=p/'build/obj/Vtb_kvslice'
   binary.write_text('#!/bin/bash\necho "KVSLICE_BOOT fake"\nif [ "$FAKE_RC" = 143 ]; then kill -TERM $$; fi\nexit "$FAKE_RC"\n');binary.chmod(0o755)
   for rc in (0,7,143):
    with self.subTest(rc=rc):
     env=dict(os.environ,PRELOAD='0',FAKE_RC=str(rc))
     r=subprocess.run(['bash',str(HERE/'run_tok.sh'),str(p/'build'),str(p/'image'),str(p/'runs'),str(rc),str(p/'vector')],env=env,capture_output=True,text=True)
     self.assertEqual(r.returncode,rc,r.stdout+r.stderr)
     self.assertEqual((p/'runs'/str(rc)/'exit').read_text().strip(),str(rc))
     self.assertIn(f'{rc} exit={rc}',r.stdout)
if __name__=='__main__':unittest.main()
