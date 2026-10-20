"""Fail closed on partial or physically impossible routed forwarding receipts."""
import unittest
import view_export as ve

GOOD = '''OT_FC_DRIVER BUFx12f_ASAP7_75t_R u.u_fcb_ck.u_cell
OT_FC_METRIC arrival_max_rise 12.45
OT_FC_METRIC arrival_min_rise 12.20
OT_FC_METRIC arrival_max_fall 13.65
OT_FC_METRIC arrival_min_fall 13.39
OT_FC_METRIC slew_max_rise 5.55
OT_FC_METRIC slew_max_fall 5.49
OT_FC_DRIVER_METRIC arrival_max_rise 12.24
OT_FC_DRIVER_METRIC arrival_min_rise 11.99
OT_FC_DRIVER_METRIC arrival_max_fall 13.44
OT_FC_DRIVER_METRIC arrival_min_fall 13.18
OT_FC_DRIVER_METRIC slew_max_rise 5.54
OT_FC_DRIVER_METRIC slew_max_fall 5.48
OT_FC_ROOT clk_in
OT_FC_CHAIN BUFx12f_ASAP7_75t_R u.u_fcb_ck.u_cell
OT_FC_ROLE BUFx12f_ASAP7_75t_R u.u_fcb_ck.u_cell A Y A 0
OT_FC_LIB BUFx12f_ASAP7_75t_R native_TT A
OT_FC_SENSE positive_unate
OT_FC_WAVE 23 377
OT_FC_PHASE arrival_max_rise 0 23
OT_FC_PHASE arrival_min_rise 0 23
OT_FC_PHASE arrival_max_fall 1 377
OT_FC_PHASE arrival_min_fall 1 377
'''

class ForwardedClock(unittest.TestCase):
    def test_missing_provenance_and_impossible_arcs_fail(self):
        for bad in (GOOD.replace('OT_FC_ROOT clk_in', ''),
                    GOOD.replace('OT_FC_METRIC arrival_min_rise 12.20\n', ''),
                    GOOD.replace('12.20', 'nan'), GOOD.replace('12.20', '-12.20'),
                    GOOD.replace('12.20', '13.20'),
                    GOOD.replace('arrival_max_rise 0 23', 'arrival_max_rise 1 377'),
                    GOOD.replace('positive_unate', 'negative_unate'),
                    GOOD.replace('OT_FC_LIB BUFx12f_ASAP7_75t_R native_TT A', ''),
                    GOOD + 'OT_FC_METRIC arrival_min_rise 12.20\n',
                    '\n'.join(GOOD.splitlines()[1:])):
            with self.subTest(log=bad), self.assertRaises(ve.VerdictError):
                ve.forwarded_clock_receipt(bad, 'ff', 'odb', 'spef')

    def test_physical_provenance_survives_receipt(self):
        r = ve.forwarded_clock_receipt(GOOD, 'tt', 'odb123', 'spef456')
        self.assertEqual(r['odb_sha256'], 'odb123')
        self.assertEqual(r['spef_sha256'], 'spef456')
        self.assertEqual(r['clk_in_to_clk_out_ps']['arrival_max_rise'], 12.45)
        self.assertTrue(r['direct_root_buffer'])
        self.assertAlmostEqual(r['output_net_delta_ps']['arrival_max_rise'], 0.21)
        self.assertIsNone(ve.forwarded_clock_receipt('OT_EXPORT_DONE', 'tt', 'a', 'b'))


class NativeModelMerge(unittest.TestCase):
    PIN = '''pin("clk_out") {
 direction : output;
 timing() {
  related_pin : "clk_in";
  timing_type : combinational;
  timing_sense : positive_unate;
  cell_rise(t) { values("12,14"); }
  cell_fall(t) { values("13,15"); }
  rise_transition(t) { values("5,6"); }
  fall_transition(t) { values("5,6"); }
 }
}'''

    def test_only_the_native_forwarding_pin_is_replaced(self):
        main = 'cell(x) {\npin("clk_out") { direction : output; }\npin("o[0]") { direction : output; }\n}'
        comb = 'cell(x) {\n' + self.PIN + '\n}'
        got = ve.merge_forwarded_clock_model(main, comb)
        self.assertIn(self.PIN, got)
        self.assertEqual(main.replace('pin("clk_out") { direction : output; }', ''), got.replace(self.PIN, ''))
        for bad in (comb.replace('"clk_in"', '"clk_out"'),
                    comb.replace('combinational', 'rising_edge'),
                    comb.replace('positive_unate', 'negative_unate'),
                    comb.replace('fall_transition(t)', 'missing(t)')):
            with self.assertRaises(ve.VerdictError):
                ve.merge_forwarded_clock_model(main, bad)

class DeclaredForwarding(unittest.TestCase):
    def test_named_inverter_derives_polarity_and_opposite_phase(self):
        log = GOOD.replace('clk_in', 'ck').replace('clk_out', 'ck_o')
        log = log.replace('positive_unate', 'negative_unate').replace(' A Y A 0', ' A Y !A 1').replace('native_TT A', 'native_TT !A')
        log = log.replace('rise 0 23', 'rise 1 377').replace('fall 1 377', 'fall 0 23')
        rec = ve.forwarded_clock_receipt(log, 'tt', 'odb', 'spef', 'ck', 'ck_o', required=True)
        self.assertEqual(rec['timing_sense'], 'negative_unate')
        self.assertEqual(rec['root_waveform_ps'], [23, 377])
        self.assertEqual(rec['output_rise_input_edge'], 'fall')
        pin = NativeModelMerge.PIN.replace('clk_in', 'ck').replace('clk_out', 'ck_o').replace('positive_unate', 'negative_unate')
        main = 'cell(x) { pin("ck_o") { direction : output; } ff(a,b) { next_state : "D"; } }'
        got = ve.merge_forwarded_clock_model(main, pin, 'ck', 'ck_o', rec['timing_sense'])
        self.assertEqual(main.replace('pin("ck_o") { direction : output; }', ''), got.replace(pin, ''))
        with self.assertRaises(ve.VerdictError):
            ve.merge_forwarded_clock_model(main, pin, 'ck', 'ck_o', 'positive_unate')

    def test_declaration_rejects_missing_ports_and_unsafe_names(self):
        self.assertIn('OT_FC_DECLARED_PORT_MISSING', ve.forwarded_clock_tcl('ck', 'ck_o', explicit=True))
        for pair in [('a;exit', 'b'), ('a', 'a'), ('ck[0]', 'ck_o')]:
            with self.assertRaises(ve.VerdictError):
                ve.forwarded_clock_tcl(*pair)
        with self.assertRaises(ve.VerdictError):
            ve.forwarded_clock_receipt('OT_EXPORT_DONE', 'tt', 'a', 'b', required=True)


class ClockOutputClassification(unittest.TestCase):
    def test_only_combinational_paths_from_clock_entries_are_clock_outputs(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
        import pinreg_audit as pa
        lib = dict(pins={
            'clk_out': dict(dir='output', clock=False, arcs=[('combinational', 'clk_in', {})]),
            'bad_data': dict(dir='output', clock=False, arcs=[('combinational', 'data_in', {})]),
        })
        m = pa.pin_metrics(lib, {'clk_in': {}})
        self.assertEqual(m['clk_out']['dir'], 'clock_out')
        self.assertEqual(m['clk_out']['comb'], [])
        self.assertEqual(m['bad_data']['comb'], ['data_in'])


if __name__ == '__main__':
    unittest.main()
