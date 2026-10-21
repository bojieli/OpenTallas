"""Production typed-phase contract mocks; actual OpenROAD fixture remains required."""
import os
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
FLOW = ROOT / 'physical/common_flow'
MOCK = Path(__file__).with_name('staged_lrt_mock.tcl')

class StagedLrt(unittest.TestCase):
    def run_case(self, mode, batch):
        env = {k: v for k, v in os.environ.items() if not k.startswith(('OT_LRT_', 'OT_PG_'))}
        env['OT_LRT_BATCH'] = str(batch)
        with tempfile.TemporaryDirectory() as temp:
            r = subprocess.run(['tclsh', str(MOCK), str(FLOW), temp, mode], env=env,
                               text=True, capture_output=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r.stdout

    def test_canonical_balancing_bytes_unchanged(self):
        source = (FLOW / 'clock_spine.tcl').read_text()
        additions = ["  # Typed source-record taps execute only after this root is balanced, before protection.\n"
                     "  if {[info exists ::ot_sp_record_taps_v1]} {\n"
                     "    if {[ot_srt::apply $port]} {ot_sp_bind_pg}\n  }\n",
                     "  if {[info exists ::ot_sp_record_taps_v1]} {ot_srt::protected $port}\n"]
        for addition in additions:
            self.assertEqual(source.count(addition), 1)
            source = source.replace(addition, '')
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),
                         'aab59f9a4f61ffbbaefa56c611d6793f1e3e59e40e256506de269ed902fd7d83')

    def test_default_worker_identical_to_current_published_helper(self):
        # Source-only local differential against ROOT's selected current helper;
        # git show reads the existing local object, never a network dependency.
        baseline = subprocess.check_output(['git', 'show',
            '8292524470ffd9ef8a381d1969c789e843a30e19:physical/common_flow/landed_raw_tap.tcl'], cwd=ROOT)
        self.assertEqual(hashlib.sha256(baseline).hexdigest(),
                         '58d7864b21b31e8e7ef395d12be7be0dd6c47123c6f6b1b191c1e3f9a5fff273')
        with tempfile.TemporaryDirectory() as temp:
            old = Path(temp)/'landed_raw_tap.tcl'; old.write_bytes(baseline)
            (Path(temp)/'native_pg_binding.tcl').write_bytes((FLOW/'native_pg_binding.tcl').read_bytes())
            env = {k: v for k, v in os.environ.items() if not k.startswith(('OT_LRT_', 'OT_PG_'))}
            for batch in (0, 1):
                env['OT_LRT_BATCH'] = str(batch)
                traces = []
                for helper in (old, FLOW/'landed_raw_tap.tcl'):
                    r = subprocess.run(['tclsh', str(MOCK.with_name('lrt_batched_mock.tcl')), str(helper)],
                        env=env, text=True, capture_output=True, timeout=30)
                    self.assertEqual(r.returncode, 0, r.stderr)
                    traces.append((r.stdout, r.stderr))
                self.assertEqual(*traces)

    def test_real_worker_serial_and_batched(self):
        for batch in (0, 1):
            with self.subTest(batch=batch):
                out = self.run_case('positive', batch)
                self.assertIn('STAGED_LRT PASS', out)
                self.assertEqual(out.count('OT_SPINE_RECORD_TAP REMEASURE'), 2)

    def test_source_ownership_and_finalization_refusals(self):
        for mode in ('wrong-owner', 'unowned', 'wrong-master', 'target', 'hash',
                     'missing-source', 'unknown-field', 'extra-target', 'buffer',
                     'plan-change', 'legacy-target-change', 'knob-change', 'protected', 'foreign-net',
                     'builder-input', 'builder-output', 'non-target-leaf', 'foreign-ref', 'root-unprotect', 'premature', 'unprotected', 'endpoint-change', 'tap-unprotect', 'readmit-after-build', 'duplicate'):
            for batch in (0, 1):
                with self.subTest(mode=mode, batch=batch):
                    out = self.run_case(mode, batch)
                    self.assertIn('MUTANT_CAUGHT ' + mode, out)
                    if mode in ('builder-input', 'builder-output', 'non-target-leaf'):
                        self.assertIn('changed final builder/leaf connection', out)

if __name__ == '__main__':
    unittest.main()
