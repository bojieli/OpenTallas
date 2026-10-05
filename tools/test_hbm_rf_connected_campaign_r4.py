#!/usr/bin/env python3
"""Independent diagnosis, preservation and mocked lifecycle; no actual RTL jobs."""
import ast,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
import full_sm_rf_verilator_gate as G
import run_hbm_rf_connected_campaign_r4 as R
import prepare_hbm_rf_connected_campaign_r4 as P
import test_hbm_rf_connected_runner as Prior
class Diagnosis(unittest.TestCase):
    def test_failing_expression_raises_before_helper(self):
        src=P.blob('a207908e2b7a7872f608163ddeeb997cd40907ba','tools/run_hbm_rf_connected_gate.py').decode()
        line=next(x.strip() for x in src.splitlines()if "out/'progress-'" in x)
        fake=Mock();ns=dict(G=fake,out=Path('/tmp/does-not-write'),target='DS',name='frontend',receipt={})
        with self.assertRaisesRegex(TypeError,'PosixPath.*str'):exec(line,ns)
        fake.write_new.assert_not_called()
        arg=ast.parse(line).body[0].value.args[0]
        self.assertIsInstance(arg.op,ast.Add)
    def test_helper_accepts_Path_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'progress-DS-frontend.json';G.write_new(p,b'evidence')
            self.assertEqual(p.read_bytes(),b'evidence')
            with self.assertRaises(FileExistsError):G.write_new(p,b'overwrite')
            self.assertEqual(p.read_bytes(),b'evidence')
    def test_additive_proposal_regenerates_and_preserves_sources(self):
        self.assertEqual(P.prepare(),json.loads((P.OUT/P.PROPOSAL).read_text()))
    def test_only_import_differs_from_prior_corrected_runner(self):
        old=P.blob(P.BASE,'tools/run_hbm_rf_connected_gate.py').decode()
        self.assertEqual((P.ROOT/'tools/run_hbm_rf_connected_campaign_r4.py').read_text(),old.replace('import prepare_hbm_rf_connected_gate as P','import prepare_hbm_rf_connected_campaign_r4 as P'))
class AdditiveLifecycle(Prior.Caps):
    def setUp(self):
        self.r=patch.object(Prior,'R',R);self.p=patch.object(Prior,'P',P)
        self.r.start();self.p.start();self.addCleanup(self.r.stop);self.addCleanup(self.p.stop)
if __name__=='__main__':unittest.main(verbosity=2)
