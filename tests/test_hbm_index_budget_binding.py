"""Reject stale targets and partial compensation; never mutate live closure state."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('hbm_binding', ROOT / 'tools/budgets/check_hbm_index_binding.py')
binding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(binding)


class BindingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        record = json.loads((ROOT / binding.RECORD / 'binding.json').read_text())
        for name in record['inputs']:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def run_check(self):
        return binding.check(self.root, self.root / binding.RECORD / 'jobs')

    def mutate(self, relative, change):
        path = self.root / relative
        obj = json.loads(path.read_text())
        change(obj)
        path.write_text(json.dumps(obj))

    def sheet(self, change):
        self.mutate(binding.BUDGET / 'sheets/hfd_index_q_b2.json', change)

    def test_valid_plan_reports_stale_jobs_without_signoff(self):
        result = self.run_check()
        self.assertEqual(result['verdict'], 'PASS')
        self.assertFalse(result['signoff_claim'])
        self.assertFalse(result['active_main_validated'])
        self.assertFalse((self.root / 'physical/hbm_accel_die_views/insertion_override.json').exists())
        self.assertFalse((self.root / 'tools/budgets/common.py').exists())
        self.assertEqual(len(result['jobs']), 5)
        self.assertTrue(all(j['stale_binding'] and j['mean_gate_pass'] for j in result['jobs']))
        b2 = next(j for j in result['jobs'] if '_b2_' in j['job'])
        self.assertEqual(b2['boundary_max_above_approved_target_ps'], 12)

    def test_old_target_rejected(self):
        self.sheet(lambda j: j['clock']['internal_insertion'].update(target_ss=900))
        with self.assertRaisesRegex(ValueError, 'compensated replay'):
            self.run_check()

    def test_missing_ocv_rejected(self):
        self.sheet(lambda j: j['interfaces'][0].update(skew_ps=64))
        with self.assertRaisesRegex(ValueError, 'compensated replay'):
            self.run_check()

    def test_entry_tamper_rejected(self):
        self.sheet(lambda j: j['clock']['entry_target_ss_ps'].update(mean=3000))
        with self.assertRaisesRegex(ValueError, 'compensated replay'):
            self.run_check()

    def test_wrong_schema_rejected(self):
        self.sheet(lambda j: j.update(schema='legacy'))
        with self.assertRaisesRegex(ValueError, 'compensated replay'):
            self.run_check()

    def test_source_mismatch_rejected(self):
        self.mutate(binding.BUDGET / 'inputs/provenance.json',
                    lambda j: j['die_models']['hbm'].update(commit='0' * 40))
        with self.assertRaisesRegex(ValueError, 'provenance/model source mismatch'):
            self.run_check()

    def test_helper_snapshot_tamper_rejected(self):
        path = self.root / binding.SNAPSHOT / 'tools/budgets/common.py'
        path.write_text(path.read_text() + '\n# altered\n')
        with self.assertRaisesRegex(ValueError, 'snapshot digest mismatch'):
            self.run_check()


if __name__ == '__main__':
    unittest.main()
