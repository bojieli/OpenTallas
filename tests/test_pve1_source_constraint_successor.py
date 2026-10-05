import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'results/rtl/pve1_new_source_constraint_successor_20261003'
spec = importlib.util.spec_from_file_location('successor', ROOT / 'tools/pve1_source_constraint_successor.py')
successor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(successor)


class SourceContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan = json.loads((EVIDENCE / 'plan.json').read_text())
        for pin in self.plan['rtl_pins']:
            target = self.root / 'source' / pin['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.check_output(
                ['git', 'show', successor.SOURCE_COMMIT + ':' + pin['path']], cwd=ROOT))
        for name in ('plan.json', 'new_source_constraint.sdc', 'source_bindings.json'):
            shutil.copyfile(EVIDENCE / name, self.root / name)

    def prepare(self, **kwargs):
        return successor.prepare(self.root / 'plan.json', self.root / 'new_source_constraint.sdc',
            self.root / 'source', self.root / 'prepared', **kwargs)

    def rewrite_plan(self):
        (self.root / 'plan.json').write_text(json.dumps(self.plan))

    def test_default_off_creates_nothing(self):
        with self.assertRaisesRegex(ValueError, 'default off'):
            self.prepare()
        self.assertFalse((self.root / 'prepared').exists())

    def test_review_bundle_does_not_claim_terminal_or_qualification(self):
        record = self.prepare(enable=True)
        self.assertFalse(record['execution_performed'])
        self.assertFalse(record['terminal_odb_captured'])
        self.assertEqual(record['qualification'], 'NOT_RUN')
        self.assertFalse(record['historical_sdc_equivalence_claim'])
        tcl = (self.root / 'prepared/new_source_resize_entry.tcl').read_text()
        self.assertLess(tcl.index('load_design'), tcl.index('/resize.tcl'))
        self.assertNotIn('2_floorplan.sdc', tcl)

    def test_relaxed_clock_or_reset_literal_refused(self):
        path = self.root / 'new_source_constraint.sdc'
        original = path.read_text()
        for before, after in [('1111', '1200'), ('-setup 60', '-setup 0'),
                              ('get_ports rst_n', 'all_inputs')]:
            with self.subTest(after=after):
                path.write_text(original.replace(before, after))
                with self.assertRaisesRegex(ValueError, 'literal constraint'):
                    self.prepare(enable=True)
                self.assertFalse((self.root / 'prepared').exists())

    def test_missing_or_substituted_rtl_inventory_refused(self):
        self.plan['rtl_pins'].pop()
        self.rewrite_plan()
        with self.assertRaisesRegex(ValueError, 'inventory'):
            self.prepare(enable=True)

    def test_changed_original_source_refused(self):
        path = self.root / 'source' / self.plan['rtl_pins'][0]['path']
        path.write_bytes(path.read_bytes() + b'\n// changed\n')
        with self.assertRaisesRegex(ValueError, 'RTL source identity'):
            self.prepare(enable=True)

    def test_constraint_declaration_or_latency_change_refused(self):
        for field in ('constraints', 'model'):
            with self.subTest(field=field):
                original = json.loads(json.dumps(self.plan))
                self.plan[field]['setup_uncertainty_ps' if field == 'constraints' else 'added_cycles'] = 1
                self.rewrite_plan()
                with self.assertRaises(ValueError):
                    self.prepare(enable=True)
                self.plan = original

    def test_retrospective_equivalence_refused(self):
        self.plan['historical_sdc_equivalence_claim'] = True
        self.rewrite_plan()
        with self.assertRaisesRegex(ValueError, 'equivalence'):
            self.prepare(enable=True)

    def test_changed_source_binding_refused(self):
        with (self.root / 'source_bindings.json').open('a') as handle:
            handle.write(' ')
        with self.assertRaisesRegex(ValueError, 'binding manifest'):
            self.prepare(enable=True)

    def test_existing_artifacts_preserved(self):
        self.prepare(enable=True)
        receipt = self.root / 'prepared/preparation.json'
        before = receipt.read_bytes()
        with self.assertRaisesRegex(ValueError, 'fresh absolute'):
            self.prepare(enable=True)
        self.assertEqual(receipt.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
