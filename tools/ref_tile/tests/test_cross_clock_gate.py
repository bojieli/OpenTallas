"""CROSS-CLOCK GATE (CX-IJ-ROOT 2026-10-18): same-tile reg->reg crossings between two clocks of a multi-clock tile.

Parser cases run everywhere; the STA cases run tools/ref_tile/cross_clock_paths.tcl on a two-clock ASAP7 fixture
(1.2 GHz stream ot_entry_0 -> 0.9 GHz serial ot_entry_1, the 3:4 VCO-tick window, the distinct-entry reserve
setup 150 / hold 100 as the generated signoff.sdc states it) in the ORFS image when docker has it.
"""
import shutil, subprocess, sys, tempfile, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE.parents[1]), str(HERE.parents[1] / 'closure_loop')]
import pre_route_gate as G

IMAGE = 'openroad/orfs:latest'
OR = '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
TWO = {'clock_port': 'clk_s', 'clock_ports': ['clk_s', 'clk_q']}
ONE = {'clock_port': 'clk'}
REPLAY = HERE / 'testdata' / 'cross_clock_dl_761317600_replay.log'


def available():
    return bool(shutil.which('docker')) and subprocess.run(['docker', 'image', 'inspect', IMAGE],
                                                           capture_output=True).returncode == 0


def items(spec, out, cts=True):
    g = G.Gate(); G.check_cross_clock(g, spec, out, cts)
    return [(i['severity'], i['check']) for i in g.items], g


class Parser(unittest.TestCase):
    def test_real_dl_replay_fails(self):
        # the old unsplit ot_hbm_su_static_cxport_dl gate state (hbm_su_cx_dl_1017, gate 20261018-045853 on ot-epyc5),
        # replayed with this path_classes.tcl: the gate that said WARN now FAILS the 3:4 crossing the route failed on
        sev, g = items(TWO, REPLAY.read_text())
        self.assertEqual(sev[0], ('FAIL', 'cross_clock'))
        self.assertIn('1045 undeclared ot_entry_0->ot_entry_1', g.items[0]['message'])
        self.assertIn('-156.2', g.items[0]['message'])
        self.assertIn('uncertainty 150.0', g.items[0]['message'])
        self.assertEqual(g.verdict, 'FAIL')

    def test_single_clock_kit_unchanged(self):
        out = "GATE_PC reg->reg 3 paths, worst slack -5.0 ps (e.g. x/D)\nGATE_XCLK_SCOPE clocks=1 names=core_clk exceptions=0\nGATE_XCLK_DONE pairs=0\n"
        self.assertEqual(items(ONE, out)[0], [])
        self.assertEqual(items(ONE, "", cts=False)[0], [])

    def test_multi_clock_needs_cts_and_completion(self):
        self.assertEqual(items(TWO, "", cts=False)[0], [('WARN', 'cross_clock')])
        self.assertEqual(items(TWO, "GATE_XCLK_SCOPE clocks=2 names=a,b exceptions=0\n")[0], [('WARN', 'cross_clock')])

    def test_remote_script_returns_lines(self):
        self.assertIn('grep -E "^GATE_(PC|XCLK)" $R/pc.log', G.REMOTE_SH)
        self.assertIn('ot_xclk_report', (HERE.parent / 'path_classes.tcl').read_text())


NET = """module t (clk_s, clk_q, d, o);
input clk_s, clk_q, d; output o;
wire q0, q1; wire [{n}:0] n;
DFFHQNx1_ASAP7_75t_R r_s (.CLK(clk_s), .D(d), .QN(q0));
assign n[0] = q0;
{chain}
DFFHQNx1_ASAP7_75t_R r_q (.CLK({cap}), .D(n[{n}]), .QN(q1));
DFFHQNx1_ASAP7_75t_R r_o (.CLK({cap}), .D(q1), .QN(o));
endmodule
"""
SDC = """create_clock -name ot_entry_0 -period 833.333 [get_ports clk_s]
create_clock -name ot_entry_1 -period 1111.111 [get_ports clk_q]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
foreach a [get_clocks ot_entry_*] { foreach b [get_clocks ot_entry_*] {
  if {[get_name $a] eq [get_name $b]} continue
  set_clock_uncertainty -setup 150 -from $a -to $b
  set_clock_uncertainty -hold 100 -from $a -to $b } }
"""
RUN = """set p /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $p/lef/asap7_tech_1x_201209.lef
read_lef $p/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty $p/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
read_liberty $p/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
source /x/cross_clock_paths.tcl
read_verilog /w/net.v
link_design t
read_sdc /w/sdc.sdc
"""


@unittest.skipUnless(available(), 'real OpenROAD ORFS image required')
class Sta(unittest.TestCase):
    def run_sta(self, extra='', cap='clk_q', n=16):
        with tempfile.TemporaryDirectory() as w:
            chain = '\n'.join(f'INVx1_ASAP7_75t_R i{i} (.A(n[{i}]), .Y(n[{i + 1}]));' for i in range(n))
            Path(w, 'net.v').write_text(NET.format(n=n, chain=chain, cap=cap))
            Path(w, 'sdc.sdc').write_text(SDC + extra)
            Path(w, 'run.tcl').write_text(RUN + 'ot_xclk_report\n')
            p = subprocess.run(['docker', 'run', '--rm', '-v', f'{w}:/w', '-v', f'{HERE.parent}:/x:ro', IMAGE, OR,
                                '-no_init', '-exit', '/w/run.tcl'], capture_output=True, text=True, timeout=120)
            self.assertEqual(p.returncode, 0, p.stdout[-3000:] + p.stderr[-2000:])
            return p.stdout

    def test_undeclared_crossing_fails_with_signoff_reserve(self):
        out = self.run_sta()
        sev, g = items(TWO, out)
        self.assertIn(('FAIL', 'cross_clock'), sev, out)
        fail = [i for i in g.items if i['severity'] == 'FAIL'][0]['message']
        self.assertIn('ot_entry_0->ot_entry_1', fail)
        self.assertIn('uncertainty 150.0', fail)

    def test_short_crossing_inside_the_window_passes(self):
        sev, _ = items(TWO, self.run_sta(n=2))
        self.assertNotIn(('FAIL', 'cross_clock'), sev)

    def test_declared_multicycle_is_not_counted(self):
        out = self.run_sta('set_multicycle_path -setup 2 -from [get_cells r_s] -to [get_cells r_q]\n'
                           'set_multicycle_path -hold 1 -from [get_cells r_s] -to [get_cells r_q]\n')
        sev, g = items(TWO, out)
        self.assertNotIn(('FAIL', 'cross_clock'), sev, out)
        self.assertIn('declared=1', out)
        self.assertIn('declared_kinds=multicycle', out)

    def test_declared_false_path_and_max_delay_are_not_counted(self):
        for extra in ('set_false_path -from [get_clocks ot_entry_0] -to [get_clocks ot_entry_1]\n',
                      'set_max_delay -ignore_clock_latency 700 -from [get_pins r_s/CLK] -to [get_pins r_q/D]\n'
                      'set_min_delay 0 -from [get_pins r_s/CLK] -to [get_pins r_q/D]\n',
                      'set_clock_groups -asynchronous -group [get_clocks ot_entry_0] -group [get_clocks ot_entry_1]\n'):
            out = self.run_sta(extra)
            sev, _ = items(TWO, out)
            self.assertNotIn(('FAIL', 'cross_clock'), sev, extra + out)
            self.assertIn('violating=0', out)

    def test_single_clock_design_reports_scope_only(self):
        out = self.run_sta(cap='clk_s')
        self.assertIn('GATE_XCLK_SCOPE clocks=1', out)
        self.assertNotIn('GATE_XCLK launch', out)
        self.assertEqual(items(ONE, out)[0], [])


if __name__ == '__main__':
    unittest.main()
