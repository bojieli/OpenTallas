"""Source/clock completeness guards for propagated physical clock diagnostics."""
import json
from pathlib import Path
import tempfile
import unittest
from physical_die_clock_sta import emit,sha


class PhysicalClockSTATests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.candidate=self.root/'candidate.json';self.dump=self.root/'dump.tsv';self.binding=self.root/'binding.json'
        self.candidate.write_text(json.dumps(dict(entries=[dict(pin='tile/ck[0]')],domains={
            'serial':dict(root='sp_collective/pll_serial[0]')})))
        self.dump.write_text('T\ttile/ck[0]\tMASTER\t0\t0\tROOT\t-\t-\n')
        self.binding.write_text(json.dumps(dict(bound={})))

    def tearDown(self):self.temp.cleanup()

    def test_missing_real_load_refuses_native_timing(self):
        with self.assertRaisesRegex(ValueError,'1 missing loads, 1 missing child insertions'):
            emit(self.candidate,self.dump,self.binding,self.root,self.root/'out')
        coverage=json.loads((self.root/'out/load_coverage.json').read_text())
        self.assertEqual(coverage['missing_entry_loads'],1)
        self.assertFalse((self.root/'out/propagated_tt.tcl').exists())

    def test_partial_scope_preserves_uncertainty_and_physical_delivery(self):
        c=emit(self.candidate,self.dump,self.binding,self.root,self.root/'out',True)
        self.assertEqual(c['scope'],'PARTIAL_LOAD_DIAGNOSTIC_NO_NATIVE_CLOCK_QUALIFICATION')
        for corner in ('tt','ff'):
            text=(self.root/f'out/propagated_{corner}.tcl').read_text()
            self.assertIn('set_clock_uncertainty -setup 210',text)
            self.assertIn('set_clock_uncertainty -hold 75',text)
            self.assertIn('set_propagated_clock',text)
            self.assertNotIn('set_clock_latency',text)
            self.assertNotIn('set_false_path',text)

    def test_forwarded_clock_cannot_become_independent_ideal_root(self):
        row=json.loads(self.candidate.read_text())
        row['domains']={'col70':dict(root='cf70/co[0]')}
        self.candidate.write_text(json.dumps(row))
        with self.assertRaisesRegex(ValueError,'native generated-clock/ratio contract'):
            emit(self.candidate,self.dump,self.binding,self.root,self.root/'out',True)

    def test_changed_source_library_is_refused_even_for_diagnostic(self):
        path=self.root/'lib.lib';path.write_text('cell(MASTER) {}')
        files={corner:dict(path='lib.lib',sha256=sha(path)) for corner in ('tt','ff')}
        self.binding.write_text(json.dumps(dict(bound={'MASTER':dict(files=files)})))
        path.write_text('cell(DIFFERENT_SOURCE) {}')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            emit(self.candidate,self.dump,self.binding,self.root,self.root/'out',True)


if __name__=='__main__':unittest.main()
