"""Execute the actual collector against a finite Tcl ODB/STA interface fixture."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import pve1_odb_endpoint_audit as audit


class NativeCollectorMockTests(unittest.TestCase):
    def collect(self, scenario):
        with tempfile.TemporaryDirectory() as tmp:
            rows = Path(tmp) / 'rows'
            sdc = Path(tmp) / 'canonical.sdc'
            result = subprocess.run(['tclsh', str(ROOT / 'tests/fixtures/pve1_odb_endpoint_mock.tcl'),
                scenario, str(ROOT / 'tools/pve1_odb_endpoint_audit.tcl'), str(rows), str(sdc),
                str(ROOT / 'results/rtl/pve1_new_source_constraint_successor_20261003/new_source_constraint.sdc')],
                capture_output=True, text=True)
            data = list(audit.decode_rows(rows)) if rows.exists() else []
            return result, data, sdc.read_text() if sdc.exists() else ''

    def test_complete_collector_corner_checks_and_iterator_lifecycle(self):
        result, data, sdc = self.collect('positive')
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = audit.audit(data, sdc, final=True)
        self.assertEqual(receipt['endpoint_count'], 2)
        self.assertFalse(receipt['physical_signoff'])
        self.assertEqual({r[2:4] for r in data if r[0] == 'timing'}, {('WC', 'max'), ('BC', 'min')})
        self.assertEqual(len([r for r in data if r[0] == 'master_pin']), 8)
        self.assertEqual(data[-1], ('complete', '1'))

    def test_reset_only_missing_graph_endpoint_has_explicit_witness(self):
        result, data, sdc = self.collect('reset_only')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(('non_graph_endpoint', 'reg/RN'), data)
        self.assertEqual(audit.audit(data, sdc, final=True)['reset_only_endpoints'], 1)

    def test_native_api_error_cannot_generate_completion(self):
        result, data, sdc = self.collect('unsupported_api')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('invalid command name "sta::vertex_iterator"', result.stderr)
        self.assertNotIn(('complete', '1'), data)
        self.assertEqual(sdc, '')

    def test_actual_collector_negative_witnesses(self):
        for scenario, witness in [
            ('mixed_reset_no_path', 'missing/unconstrained timing; reset exception is not an endpoint waiver'),
            ('missing_corner', 'missing/unconstrained timing; reset exception is not an endpoint waiver'),
            ('disabled_constraint', 'disabled timing check requires explicit structural review'),
            ('missing_lib_pin', 'duplicate or unmatched full-netlist master pin view'),
            ('unclocked', 'unclocked or multiple-clock sequential pin'),
            ('unconstrained', 'missing/unconstrained timing; reset exception is not an endpoint waiver'),
            ('negative', 'terminal timing violation'),
            ('missing_endpoint', 'non-graph functional endpoint requires structural review'),
            ('check_setup_failure', 'incomplete native capture or failed check_setup')]:
            with self.subTest(scenario=scenario):
                result, data, sdc = self.collect(scenario)
                self.assertEqual(result.returncode, 0, result.stderr)
                with self.assertRaises(ValueError) as refused:
                    audit.audit(data, sdc, final=True)
                self.assertEqual(str(refused.exception), witness)

    def test_macro_arc_delay_signature_retained_and_qualification_held(self):
        result, data, sdc = self.collect('macro')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(('macro_arc', 'reg', 'reg/CLK', 'reg/D', 'setup', 'WC max clk-q 12; BC min clk-q 4'), data)
        with self.assertRaisesRegex(ValueError, 'memory/BLOCK'):
            audit.audit(data, sdc, final=True)


if __name__ == '__main__':
    unittest.main()
