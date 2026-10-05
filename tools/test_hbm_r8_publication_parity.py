#!/usr/bin/env python3
"""Read-only publication/worker parity and pure GO validation; never admits or runs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('results/uarch/hbm_runtime_calibration_r8_20261002')
WORKER = Path(json.loads((ROOT / BASE / 'qualified_DS_binary.json').read_text())['source_root'])
SOURCE = '10e6bcde11e2f0790f6c153d768a6fa0c1be2954'


def worker_check(target, go):
    code = '''import json,sys
from pathlib import Path
import prepare_hbm_runtime_calibration_r8 as P
import run_hbm_runtime_calibration_r8 as R
target=sys.argv[1];go=json.loads(sys.stdin.read())
p=P.OUT/(target+'_prepared_gate.json')
assert p.read_bytes()==(json.dumps(P.prepare_target(target),indent=2,sort_keys=True)+'\\n').encode()
R.CAPS=P.caps_for(target)
R.validate_go(go,p,R.G.git('rev-parse','HEAD'))
print(json.dumps({'target':target,'source_commit':R.G.git('rev-parse','HEAD'),'proposal_sha256':R.G.sha(p),'pure_validate_go':'PASS','execution':False},sort_keys=True))
'''
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    return subprocess.run([sys.executable, '-B', '-c', 'import sys;sys.path.insert(0,"tools");\n'+code, target], cwd=WORKER, env=env, input=json.dumps(go), text=True, capture_output=True, timeout=60)


def candidate(target):
    go = json.loads((ROOT / BASE / (target+'_GO_template.json')).read_text())
    go.update(admitted=True, source_commit=SOURCE,
              unit='hbm-'+target.lower()+'-runtime-calibration-parent-20261002-r2.service',
              output_path='/tmp/hbm-'+target.lower()+'-runtime-calibration-parent-20261002-r2',
              admission_record_path='results/rtl/hbm_'+target.lower()+'_runtime_calibration_parent_20261002_r2/GO.json')
    return go


class PublicationParity(unittest.TestCase):
    def test_frozen_worker_identity(self):
        self.assertEqual(subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORKER,text=True).strip(),SOURCE)
        self.assertEqual(subprocess.check_output(['git','status','--porcelain'],cwd=WORKER,text=True),'')

    def test_exact_bytes_and_every_tool_pin(self):
        for target in ('DS','Qwen'):
            main=(ROOT/BASE/(target+'_prepared_gate.json')).read_bytes()
            self.assertEqual(main,(WORKER/BASE/(target+'_prepared_gate.json')).read_bytes())
            proposal=json.loads(main)
            for path,pin in proposal['gate_tool_sha256'].items():
                self.assertEqual((ROOT/path).read_bytes(),(WORKER/path).read_bytes(),path)
                self.assertEqual(hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),pin,path)
            self.assertEqual(candidate(target)['proposal_sha256'],hashlib.sha256(main).hexdigest())

    def test_real_worker_prepare_and_candidate_GO(self):
        for target in ('DS','Qwen'):
            result=worker_check(target,candidate(target))
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['pure_validate_go'],'PASS')

    def test_original_failed_GO_refused(self):
        for target,folder in [('DS','ds'),('Qwen','qwen')]:
            go=json.loads((ROOT/'results/rtl/hbm_runtime_split_preflight_owner_20261002_r1'/folder/'GO.json').read_text())
            result=worker_check(target,go)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('GO source/proposal mismatch',result.stderr)

if __name__=='__main__':
    unittest.main()
