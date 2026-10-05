"""Source preparation checks only. These tests do not compile or simulate RTL."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from qwen_hbm_r14_metadata import emit
from qwen_hbm_r14_journal_audit import audit
from run_hbm_finite_stage_r14 import compile_argv, manifest

class Preflight(unittest.TestCase):
    def test_actual_metadata_reproduction(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'metadata.svh';record=emit(p)
            self.assertEqual(p.read_bytes(),(ROOT/'rtl/test/model_ready_hbm_r14/qwen_stage_metadata_r14.svh').read_bytes())
            self.assertEqual((record['writers_position0'],record['writers_position1'],record['readers']),(272,272,288))
            self.assertFalse(record['payload'])

    def test_manifest_includes_real_macros_and_irs(self):
        paths=manifest()
        self.assertIn('rtl/abi3/ot_a3_issue_record_store.sv',paths)
        for name in ['64x512','128x256']:
            self.assertEqual(sum(name in p and p.endswith('.v') for p in paths),1)
        argv=compile_argv(Path('/tmp/never_execute_r14_test'))
        self.assertEqual(argv[argv.index('--threads')+1],'1')
        self.assertEqual(argv[argv.index('-j')+1],'1')
        self.assertIn('--binary',argv)

    def test_partial_auditor_rejects_early_backing(self):
        # Synthetic journal tests the auditor only, never a provider result.
        header='event\tobserve_ps\tstack\tcycle\top\tpc\tbank\trow\tsector\ttag\tbeat\tproducer\ttransport\tcaller\tIRSslot\tIRSserial\taux\n'
        cmd='CMD\t10000\t0\t0\t3\t0\t0\t0\t0\t1\t0\t0\t0\t0\t0\t0\t0\n'
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'journal.tsv'
            for delta,expected in [(7273,'FAIL'),(7274,'PARTIAL_CHECKS_PASS_NOT_PROVIDER_PASS')]:
                backing=f'BACKING_WRITE\t{10000+delta}\t0\t0\t3\t0\t0\t0\t0\t1\t0\t0\t0\t0\t0\t0\t0\n'
                p.write_text(header+cmd+backing)
                self.assertEqual(audit(p)['status'],expected)

if __name__=='__main__': unittest.main()
