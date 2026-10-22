"""TOKc-GRAY 10-22: the async_gray tie-driver verdict is computed once per actual net and applied to every async pin on
that net (hdie_svc_vm_kshare_r4: thousands of tied DFFASRHQNx1 SET/RESET pins, ~0.12 s per pin re-scanning the same
tie net).  The verdict must equal the original per-pin scan for every pin; a different net is always scanned again; a
failing net fails every pin on it and no pin elsewhere.  OpenSTA timing-graph fixture only (generic Liberty).
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import async_gray_fifo_constraints as A
from test_async_gray_fifo_constraints import STA, spec, ROOT

LIB = r'''library(probe) { delay_model : table_lookup; time_unit : "1ps"; capacitive_load_unit(1,ff); nom_voltage : 0.7; nom_temperature : 25; nom_process : 1;
cell(TIEHIx1_ASAP7_75t_R) {area : 1; pin(H){direction : output; function : "1";}}
cell(TIELOx1_ASAP7_75t_R) {area : 1; pin(L){direction : output; function : "0";}}
cell(INVx1_ASAP7_75t_R) {
 area : 1;
 pin(A) { direction : input; capacitance : 1; }
 pin(Y) {
  direction : output;
  function : "!A";
  timing() { related_pin : "A"; timing_sense : negative_unate; cell_rise(scalar){values("3");} cell_fall(scalar){values("3");} rise_transition(scalar){values("1");} fall_transition(scalar){values("1");} }
 }
}
cell(DFFR) {area : 1; ff(IQ,IQN){clocked_on : "C"; next_state : "D"; clear : "!R";}
 pin(C){direction : input; capacitance : 1; clock : true;}
 pin(D){direction : input; capacitance : 1; timing(){related_pin : "C"; timing_type : setup_rising; rise_constraint(scalar){values("2");}fall_constraint(scalar){values("2");}}}
 pin(R){direction : input; capacitance : 1; timing(){related_pin : "C"; timing_type : recovery_rising; rise_constraint(scalar){values("2");}fall_constraint(scalar){values("2");}}}
 pin(Q){direction : output; function : "IQ"; timing(){related_pin : "C"; timing_type : rising_edge; timing_sense : positive_unate; cell_rise(scalar){values("3");}cell_fall(scalar){values("3");}rise_transition(scalar){values("1");}fall_transition(scalar){values("1");}}
  timing(){related_pin : "R"; timing_type : clear; timing_sense : positive_unate; cell_rise(scalar){values("3");}cell_fall(scalar){values("3");}rise_transition(scalar){values("1");}fall_transition(scalar){values("1");}}}}
}
'''
# a, b: two identical flops on one TIEHI net (shared key -> one scan); c: same flop on its own TIEHI net (different key
# -> its own scan); dd, e: a net driven by an inverter of a TIELO (not a tie cell -> seeded FAIL for both, nobody else).
NETLIST = '''module top(input clk, input d, output qa, output qb, output qc, output qd, output qe);
  wire n1, n2, n3, n4;
  TIEHIx1_ASAP7_75t_R t1(.H(n1));
  TIEHIx1_ASAP7_75t_R t2(.H(n2));
  TIELOx1_ASAP7_75t_R t3(.L(n4));
  INVx1_ASAP7_75t_R i3(.A(n4), .Y(n3));
  DFFR a(.C(clk), .D(d), .R(n1), .Q(qa));
  DFFR b(.C(clk), .D(d), .R(n1), .Q(qb));
  DFFR c(.C(clk), .D(d), .R(n2), .Q(qc));
  DFFR dd(.C(clk), .D(d), .R(n3), .Q(qd));
  DFFR e(.C(clk), .D(d), .R(n3), .Q(qe));
endmodule
'''
# The pre-change per-pin scan, verbatim, as the oracle.
ORACLE = r'''proc oracle_tied {pin} {
  set tied 1
  foreach d [get_pins -quiet -of_objects [get_nets -quiet -of_objects $pin]] {
    if {[get_property $d direction] ne "output"} continue
    if {![regexp {^TIE(HI|LO)x} [get_property [get_cells -quiet -of_objects $d] ref_name]]} {set tied 0}
  }
  return $tied
}
'''


def run(order):
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        (t / 't.lib').write_text(LIB)
        (t / 't.v').write_text(NETLIST)
        tcl = [f'read_liberty {{{t}/t.lib}}', f'read_verilog {{{t}/t.v}}', 'link_design top',
               'create_clock -name c -period 1000 [get_ports clk]', A.TCL, ORACLE,
               'set ::ot_ag_tie_memo {}', 'set ::ot_ag_tie_stats {}',
               'set cells [dict create a core b core c core dd core e core]']
        for p in order:
            tcl.append(f'set v [expr {{![catch {{ot_ag_async_control [get_pins {p}/R] $cells {{}}}} msg]}}]; '
                       f'puts "VERDICT {p} $v [oracle_tied [get_pins {p}/R]] $msg"')
        tcl.append('puts "STATS [dict get [dict merge {scanned 0 reused 0} $::ot_ag_tie_stats] scanned] '
                   '[dict get [dict merge {scanned 0 reused 0} $::ot_ag_tie_stats] reused]"')
        tcl.append('puts "MEMO $::ot_ag_tie_memo"')
        (t / 't.tcl').write_text('\n'.join(tcl) + '\nexit 0\n')
        p = subprocess.run([STA, '-exit', str(t / 't.tcl')], text=True, capture_output=True)
        log = p.stdout + p.stderr
        if p.returncode:
            raise AssertionError(log)
        verdicts = {}
        stats = memo = None
        for line in log.splitlines():
            if line.startswith('VERDICT '):
                _, pin, new, old, *msg = line.split(' ')
                verdicts[pin] = (int(new), int(old), ' '.join(msg))
            elif line.startswith('STATS '):
                stats = tuple(int(x) for x in line.split()[1:])
            elif line.startswith('MEMO '):
                memo = line[5:]
        return verdicts, stats, memo


@unittest.skipUnless(Path(STA).exists(), 'OpenSTA fixture tool required')
class TieDriverDedup(unittest.TestCase):
    def test_identical_pins_share_one_scan(self):
        v, stats, _ = run(['a', 'b'])
        self.assertEqual(stats, (1, 1))                      # 1 scan, 2 pins covered
        self.assertEqual(v['a'][0], 1); self.assertEqual(v['b'][0], 1)

    def test_different_net_rescanned(self):
        v, stats, memo = run(['a', 'b', 'c'])
        self.assertEqual(stats, (2, 1))                      # n1 once, n2 separately
        self.assertTrue(all(v[p][0] == 1 for p in 'abc'))
        self.assertIn('n1 1', memo); self.assertIn('n2 1', memo)

    def test_seeded_failing_net_fails_its_pins_only(self):
        for order in (['dd', 'a', 'e', 'b', 'c'], ['a', 'b', 'c', 'dd', 'e']):
            with self.subTest(order=order):
                v, stats, memo = run(order)
                self.assertEqual(stats, (3, 2))
                for p in ('dd', 'e'):
                    self.assertEqual(v[p][0], 0)
                    self.assertIn('asynchronous control without a register or tie driver', v[p][2])
                for p in ('a', 'b', 'c'):
                    self.assertEqual(v[p][0], 1)
                self.assertIn('n3 0', memo)

    def test_matches_per_pin_oracle(self):
        v, _, _ = run(['e', 'c', 'a', 'dd', 'b'])
        for pin, (new, old, _) in v.items():
            self.assertEqual(new, old, pin)

    def test_memo_cleared_every_ownership_pass(self):
        body = __import__('clock_entry_constraints').generate(spec(), ROOT)
        self.assertIn('set ::ot_ag_tie_memo {}\n  set ::ot_ag_tie_stats {}\n  set cells {}', body)
        self.assertIn('OT_ASYNC_GRAY TIE_DRIVER_DEDUP nets_scanned=', body)


if __name__ == '__main__':
    unittest.main()
