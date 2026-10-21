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
'''

class ForwardedClock(unittest.TestCase):
    def test_missing_provenance_and_impossible_arcs_fail(self):
        for bad in (GOOD.replace('OT_FC_ROOT clk_in', ''),
                    GOOD.replace('OT_FC_METRIC arrival_min_rise 12.20\n', ''),
                    GOOD.replace('12.20', 'nan'), GOOD.replace('12.20', '-12.20'),
                    GOOD.replace('12.20', '13.20'),
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


class NamedForwardingPair(unittest.TestCase):
    """Relay ck -> ck_o (CTS leaf + two kept inverters + output buffer)."""
    LOG = GOOD.replace('OT_FC_DRIVER BUFx12f_ASAP7_75t_R u.u_fcb_ck.u_cell',
                       'OT_FC_CHAIN BUFx2_ASAP7_75t_R output556\n'
                       'OT_FC_CHAIN INVx3_ASAP7_75t_R u_ck1/_0_\n'
                       'OT_FC_CHAIN INVx3_ASAP7_75t_R u_ck0/_0_\n'
                       'OT_FC_CHAIN BUFx4_ASAP7_75t_R clkbuf_0_ck\n'
                       'OT_FC_DRIVER BUFx2_ASAP7_75t_R output556').replace('OT_FC_ROOT clk_in', 'OT_FC_ROOT ck')

    def test_default_tcl_is_historical(self):
        self.assertIs(ve.forwarded_clock_tcl(), ve.FORWARDED_CLOCK_TCL)

    def test_named_tcl_has_no_default_names(self):
        t = ve.forwarded_clock_tcl('ck', 'ck_o')
        self.assertNotIn('clk_in', t)
        self.assertNotIn('clk_out', t)
        self.assertIn('OT_FC_ROOT ck"', t)
        self.assertIn('OT_FC_CHAIN', t)
        with self.assertRaises(ve.VerdictError):
            ve.forwarded_clock_tcl('ck]', 'ck_o')

    def test_chain_receipt(self):
        r = ve.forwarded_clock_receipt(self.LOG, 'tt', 'o', 's', 'ck', 'ck_o')
        self.assertEqual(r['input_pin'], 'ck')
        self.assertFalse(r['direct_root_buffer'])
        self.assertEqual(len(r['chain_out_to_in']), 4)
        for bad in (self.LOG.replace('OT_FC_ROOT ck', 'OT_FC_ROOT clk_in'),
                    self.LOG.replace('OT_FC_CHAIN BUFx2_ASAP7_75t_R output556\n', '')):
            with self.subTest(log=bad), self.assertRaises(ve.VerdictError):
                ve.forwarded_clock_receipt(bad, 'tt', 'o', 's', 'ck', 'ck_o')
        with self.assertRaises(ve.VerdictError):    # default pair must not accept a ck root
            ve.forwarded_clock_receipt(self.LOG, 'tt', 'o', 's')

    def test_named_merge_and_self_arc_refused(self):
        pin = NativeModelMerge.PIN.replace('clk_out', 'ck_o').replace('clk_in', 'ck')
        main = 'cell(x) {\npin("ck_o") { direction : output; }\n}'
        got = ve.merge_forwarded_clock_model(main, 'cell(x) {\n' + pin + '\n}', 'ck', 'ck_o')
        self.assertIn(pin, got)
        selfarc = pin.replace('related_pin : "ck"', 'related_pin : "ck_o"').replace('combinational', 'rising_edge')
        with self.assertRaises(ve.VerdictError):
            ve.merge_forwarded_clock_model(main, 'cell(x) {\n' + selfarc + '\n}', 'ck', 'ck_o')


class InvertedForwardingPair(unittest.TestCase):
    LOG = GOOD.replace('OT_FC_DRIVER BUFx12f_ASAP7_75t_R u.u_fcb_ck.u_cell',
                       'OT_FC_CHAIN BUF outbuf\nOT_FC_CHAIN INV invert\nOT_FC_CHAIN BUF inbuf\n'
                       'OT_FC_DRIVER BUF outbuf').replace('OT_FC_ROOT clk_in', 'OT_FC_ROOT ck') + '''
OT_FC_LIB BUF corner_tt A
OT_FC_LIB INV corner_tt !A
OT_FC_ROLE BUF outbuf A Y A 0
OT_FC_ROLE INV invert A Y !A 1
OT_FC_ROLE BUF inbuf A Y A 0
OT_FC_SENSE negative_unate
OT_FC_PHASE rise fall
OT_FC_PHASE fall rise
'''

    def test_inversion_requires_actual_loaded_functions_and_phase_map(self):
        rec = ve.forwarded_clock_receipt(self.LOG, 'tt', 'odb', 'spef', 'ck', 'ck_o', sense='negative_unate')
        self.assertEqual(rec['timing_sense'], 'negative_unate')
        self.assertEqual(rec['input_edge_for_output'], {'rise': 'fall', 'fall': 'rise'})
        self.assertEqual(sum(r['inversion'] for r in rec['native_unary_roles']), 1)
        for bad in (self.LOG.replace('OT_FC_PHASE rise fall', 'OT_FC_PHASE rise rise'),
                    self.LOG.replace('OT_FC_LIB INV corner_tt !A', ''),
                    self.LOG.replace('OT_FC_LIB INV corner_tt !A', 'OT_FC_LIB INV corner_tt A'),
                    self.LOG.replace('OT_FC_ROLE INV invert A Y !A 1', 'OT_FC_ROLE INV invert A Y A 0'),
                    self.LOG.replace('OT_FC_ROLE INV invert A Y !A 1', 'OT_FC_ROLE INV invert A Y !A 0'),
                    self.LOG + 'OT_FC_LIB INV other_corner A\n',
                    self.LOG.replace('OT_FC_SENSE negative_unate', ''),
                    self.LOG.replace('OT_FC_CHAIN INV invert', 'OT_FC_CHAIN INV other')):
            with self.subTest(log=bad), self.assertRaises(ve.VerdictError):
                ve.forwarded_clock_receipt(bad, 'tt', 'odb', 'spef', 'ck', 'ck_o', sense='negative_unate')
        with self.assertRaises(ve.VerdictError):
            ve.forwarded_clock_receipt(self.LOG, 'tt', 'odb', 'spef', 'ck', 'ck_o')

    def test_native_negative_arc_only_and_other_groups_unchanged(self):
        pin = NativeModelMerge.PIN.replace('clk_in', 'ck').replace('clk_out', 'ck_o').replace('positive_unate', 'negative_unate')
        untouched = '\npin("q") { timing() { related_pin : "ck"; timing_type : rising_edge; } }\n'
        main = 'cell(x) {\npin("ck_o") { direction : output; }' + untouched + '}'
        native = 'cell(x) {\n' + pin + '\n}'
        merged = ve.merge_forwarded_clock_model(main, native, 'ck', 'ck_o', sense='negative_unate')
        self.assertEqual(main.replace('pin("ck_o") { direction : output; }', ''), merged.replace(pin, ''))
        for bad in (native.replace('negative_unate', 'positive_unate'),
                    native.replace('related_pin : "ck"', 'related_pin : "ck_o"'),
                    native.replace('combinational', 'rising_edge')):
            with self.subTest(lib=bad), self.assertRaises(ve.VerdictError):
                ve.merge_forwarded_clock_model(main, bad, 'ck', 'ck_o', sense='negative_unate')
        with self.assertRaises(ve.VerdictError):
            ve.merge_forwarded_clock_model(main, native, 'ck', 'ck_o')

    def test_opposite_input_phase_and_native_root_proof_in_tcl(self):
        tcl = ve.forwarded_clock_tcl('ck', 'ck_o', sense='negative_unate')
        self.assertIn('find_liberty_cell', tcl)
        self.assertIn('[$ot_fc_lp function]', tcl)
        self.assertIn('if {$ot_fc_parity != 1}', tcl)
        self.assertIn('lindex $ot_fc_wave [expr {1 - $edge}]', tcl)
        self.assertIs(ve.forwarded_clock_tcl(), ve.FORWARDED_CLOCK_TCL)


if __name__ == '__main__':
    unittest.main()
