"""Source admission guards for a forest still proved on the actual mapped netlist."""
import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ref_tile as R


class SourceNative(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = 'rtl/example.sv'
        p = self.root / self.source
        p.parent.mkdir(parents=True)
        p.write_text('module example(input ck, rst_n); endmodule\n')
        self.entry = dict(source=self.source, sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                          top='example', clock='ck', reset_ports=['rst_n'],
                          first_copies={'rst_n': 12}, copies={'rst_n': 288})
        dep=self.root/'rtl/macro_bb.v';dep.write_text('module macro; endmodule\n')
        self.entry['source_dependencies']={'rtl/macro_bb.v':hashlib.sha256(dep.read_bytes()).hexdigest()}
        self.spec = dict(top='example', sources=[self.source], params={}, defines=[], clock_port='ck',
                         reset_ports=['rst_n'], pin_regs=dict(enable=False, reason='existing source boundary registers'),
                         reset_landing=dict(enable=True, stages=2, clock='ck', source_native='fixture',
                                            first_copies={'rst_n': 12}, copies={'rst_n': 288}))
        self.spec['sources'].append('rtl/macro_bb.v')
        self.patches = [patch.object(R, 'ROOT', self.root),
                        patch.object(R, 'SOURCE_NATIVE_RESET_LANDINGS', {'fixture': self.entry})]
        for p in self.patches: p.start()

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.tmp.cleanup()

    def test_preserves_required_mapped_profile_without_duplicate_wrapper(self):
        plan = R.reset_landing_plan(self.spec)
        self.assertTrue(plan['enable'])
        self.assertEqual(plan['stages'], 2)
        self.assertEqual(plan['first_copies'], {'rst_n': 12})
        self.assertEqual(plan['copies'], {'rst_n': 288})
        self.assertEqual(plan['reset_release_cycles'], 2)
        self.assertEqual(R.reset_landing_vars(self.spec), [])
        self.assertEqual(R.reset_relay_split_vars(self.spec), [])
        self.assertFalse(R.pin_wrapper(self.spec))

    def test_source_and_initialization_change_refused(self):
        p = self.root / self.source
        for text in ('module changed; endmodule\n', 'module example; reg q=1; endmodule\n'):
            p.write_text(text)
            with self.assertRaisesRegex(R.SpecError, 'fingerprint'):
                R.reset_landing_plan(self.spec)
        p.unlink()
        with self.assertRaisesRegex(R.SpecError, 'fingerprint'):
            R.reset_landing_plan(self.spec)

    def test_closed_top_parameter_define_and_source_contract(self):
        for change in (dict(top='other'), dict(params={'BYPASS': 1}), dict(defines=['BYPASS']),
                       dict(reset_ports=['other']), dict(clock_port='other'), dict(sources=[]),
                       dict(pin_regs={'enable': True}), dict(reset_relay_split={'max_loads': 32}),
                       dict(sources=[self.source,'rtl/macro_bb.v','rtl/extra.v']),
                       dict(orfs_vars={'SYNTH_PARAMETERS':'SHAPE=4'}),
                       dict(orfs_vars={'SYNTH_DEFINES':'PROGRAM=4'}),
                       dict(orfs_vars={'VERILOG_FILES':'other.v'}),dict(orfs_vars={'OT_RST_LAND':1})):
            with self.subTest(change=change), self.assertRaises(R.SpecError):
                R.reset_landing_plan(dict(self.spec, **change))

    def test_changed_dependency_refused(self):
        (self.root/'rtl/macro_bb.v').write_text('module macro; reg q=1; endmodule\n')
        with self.assertRaisesRegex(R.SpecError,'fingerprint'):R.reset_landing_plan(self.spec)

    def test_no_boolean_unknown_id_waiver_count_clock_or_age_escape(self):
        for change in (dict(source_native=True), dict(source_native=False), dict(source_native='unknown'),
                       dict(enable=False, reason='skip'), dict(stages=1), dict(clock='other'),
                       dict(first_copies={'rst_n': 11}), dict(copies={'rst_n': 287}),
                       dict(waive='skip'), dict(max_sinks=100000)):
            s = copy.deepcopy(self.spec)
            s['reset_landing'].update(change)
            with self.subTest(change=change), self.assertRaises(R.SpecError): R.reset_landing_plan(s)

    def test_unprofiled_mode_retains_old_wrapper(self):
        s = copy.deepcopy(self.spec)
        s['reset_landing'] = dict(enable=True, stages=2)
        self.assertTrue(R.pin_wrapper(s))
        self.assertIn('--orfs-var OT_RST_LAND=1', R.reset_landing_vars(s))

    def test_exact_typed_counts_at_admission_and_plan_boundaries(self):
        # The real PROMPT entry has one first copy: Python's True == 1 and
        # 1.0 == 1 must not make a malformed registry request valid.
        self.entry['first_copies'] = {'rst_n': 1}
        self.entry['copies'] = {'rst_n': 4}
        self.spec['reset_landing'].update(first_copies={'rst_n': 1}, copies={'rst_n': 4})
        self.assertEqual(R.reset_landing_plan(self.spec)['copies'], {'rst_n': 4})
        changes = [dict(stages=v) for v in (True, False, 2.0, '2')]
        changes += [dict(first_copies={'rst_n': v}) for v in (True, 1.0, '1')]
        changes += [dict(copies={'rst_n': v}) for v in (False, 4.0, '4')]
        for change in changes:
            s = copy.deepcopy(self.spec)
            s['reset_landing'].update(change)
            for call in (lambda: R.source_native_reset_landing(s, s['reset_landing']),
                         lambda: R.reset_landing_plan(s)):
                with self.subTest(change=change), self.assertRaises(R.SpecError): call()

    def test_malformed_or_duplicate_source_closure_refused(self):
        for sources in ([self.source, {}], [self.source, ['rtl/macro_bb.v']],
                        [self.source, self.source], self.source):
            with self.subTest(sources=sources), self.assertRaises(R.SpecError):
                R.reset_landing_plan(dict(self.spec, sources=sources))


if __name__ == '__main__': unittest.main()
