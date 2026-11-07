"""Functional OpenSTA paths: input->register, register->output, macro->register.

No P&R or timing thresholds are changed. The tiny Liberty models a clocked
macro and a standard flop; the same real timing graph is queried before,
during and after the production repair-scope helper.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
OPENROAD = shutil.which("openroad")


def cell(name, area):
    return r'''cell (NAME) {
  area : AREA;
  ff (IQ, IQN) { clocked_on : "CK"; next_state : "D"; }
  pin (CK) { direction : input; clock : true; capacitance : 0.001; }
  pin (D) { direction : input; capacitance : 0.001;
    timing () { related_pin : "CK"; timing_type : hold_rising;
      rise_constraint (scalar) { values ("0.010"); }
      fall_constraint (scalar) { values ("0.010"); } }
    timing () { related_pin : "CK"; timing_type : setup_rising;
      rise_constraint (scalar) { values ("0.010"); }
      fall_constraint (scalar) { values ("0.010"); } }
  }
  pin (Q) { direction : output; function : "IQ";
    timing () { related_pin : "CK"; timing_type : rising_edge;
      timing_sense : non_unate;
      cell_rise (scalar) { values ("0.005"); }
      cell_fall (scalar) { values ("0.005"); }
      rise_transition (scalar) { values ("0.005"); }
      fall_transition (scalar) { values ("0.005"); } }
  }
}
'''.replace("NAME", name).replace("AREA", str(area))


LIB = ('''library (fixture) {
  delay_model : table_lookup;
  time_unit : "1ns";
  voltage_unit : "1V";
  current_unit : "1mA";
  capacitive_load_unit (1,pf);
  nom_process : 1; nom_voltage : 1; nom_temperature : 25;
''' + cell("DFF", 1) + cell("CLOCKED_MACRO", 1000) + "}\n")
NETLIST = '''module top(input CK, DIN, output R2O, MOUT);
wire qi, qm;
DFF u_input(.CK(CK), .D(DIN), .Q(qi));
DFF u_r2o(.CK(CK), .D(qi), .Q(R2O));
CLOCKED_MACRO u_macro(.CK(CK), .D(DIN), .Q(qm));
DFF u_macro_capture(.CK(CK), .D(qm), .Q(MOUT));
endmodule
'''
LEF = '''VERSION 5.8 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;
UNITS DATABASE MICRONS 1000 ; END UNITS
MANUFACTURINGGRID 0.001 ;
LAYER M1
 TYPE ROUTING ; DIRECTION HORIZONTAL ; PITCH 0.2 ; WIDTH 0.1 ; SPACING 0.1 ;
END M1
SITE CORE
 CLASS CORE ; SIZE 1 BY 1 ; SYMMETRY X Y ;
END CORE
'''
for name, kind, size in (("DFF", "CORE", 1), ("CLOCKED_MACRO", "BLOCK", 10)):
    LEF += f"MACRO {name}\n CLASS {kind} ; ORIGIN 0 0 ; SIZE {size} BY {size} ;\n"
    if kind == "CORE":
        LEF += " SITE CORE ;\n"
    for pin, direction, use, x in (("CK", "INPUT", "CLOCK", .1), ("D", "INPUT", "SIGNAL", .4),
                                    ("Q", "OUTPUT", "SIGNAL", .7)):
        LEF += f" PIN {pin}\n  DIRECTION {direction} ; USE {use} ;\n  PORT LAYER M1 ; RECT {x} 0.1 {x+.1} 0.2 ; END\n END {pin}\n"
    LEF += f"END {name}\n"
LEF += "END LIBRARY\n"


def production_helper(mm):
    if mm:
        text = (HERE.parents[1] / "orfs_hold_mm.tcl").read_text()
        return text[text.index("proc ot_hold_scope_read {path}"):text.index("\nproc ot_repair_timing {rt_args}")]
    text = (HERE / "prd_hook.tcl").read_text()
    return text[text.index("proc ot_prd_hold_scope {body}"):text.index("\nset args [list -hold_margin")]


@unittest.skipUnless(OPENROAD, "OpenROAD required for functional STA fixture")
class NonportSTA(unittest.TestCase):
    def run_graph(self, scope, mm=False, body_error=False):
        with tempfile.TemporaryDirectory(prefix="nonport-sta-") as td:
            d = Path(td)
            (d / "fixture.lib").write_text(LIB)
            (d / "fixture.v").write_text(NETLIST)
            (d / "fixture.lef").write_text(LEF)
            setup = (f"read_liberty {{{d}/fixture.lib}}\nset_mode tc\nset_mode ff\n"
                     f"define_scene TC -mode tc -liberty {{{d}/fixture.lib}}\n"
                     f"define_scene BC -mode ff -liberty {{{d}/fixture.lib}}\n" if mm
                     else f"read_liberty {{{d}/fixture.lib}}\n")
            script = f"read_lef {{{d}/fixture.lef}}\n" + setup + f"read_verilog {{{d}/fixture.v}}\nlink_design top\n"
            modes = ["tc", "ff"] if mm else [""]
            for mode in modes:
                if mode:
                    script += f"set_mode {mode}\n"
                script += '''create_clock -name clk -period 0.833 [get_ports CK]
set_clock_uncertainty -hold 0.025 [get_clocks clk]
set_input_delay -clock clk -min -0.020 [get_ports DIN]
set_input_delay -clock clk -max 0.100 [get_ports DIN]
set_output_delay -clock clk -min 0.000 [all_outputs]
set_output_delay -clock clk -max 0.100 [all_outputs]
'''
            if mm:
                script += "set_mode tc\nset ::ot_mm_synced 1\nset ::ot_mm_stage 4_cts.sdc\n"
                script += "proc ot_hold_stats {} {return [sta::worst_slack_cmd min]}\n"
            script += production_helper(mm)
            if scope:
                script += f"\nset ::env(OT_HOLD_REPAIR_SCOPE) {scope}\n"
            script += f"\nset ::env(RESULTS_DIR) {{{d}}}\nset ::env(OT_HOLD_SCOPE_KEEP_SDC) 1\n"
            script += "proc snapshot {path} {\n"
            if mm:
                script += "set_scene BC\n"
            scenes = " -scenes BC" if mm else ""
            script += f"report_checks -path_delay min{scenes} -group_path_count 100 -endpoint_path_count 100 > $path\n"
            if mm:
                script += "report_checks -path_delay max -scenes TC -group_path_count 100 -endpoint_path_count 100 > ${path}.tc\n"
                script += "set_scene TC\n"
            script += "}\n"
            helper = "ot_hold_repair_scope" if mm else "ot_prd_hold_scope"
            script += f"snapshot {{{d}/before.rpt}}\n"
            script += f"if {{[catch {{{helper} {{snapshot {{{d}/during.rpt}}; "
            script += "error expected-body-error" if body_error else "set result ok"
            script += "}} msg]} {\n"
            script += 'if {$msg ne "expected-body-error"} {error $msg}\n}\n'
            script += f"snapshot {{{d}/after.rpt}}\n"
            if mm:
                script += 'if {[sta::cmd_mode_name] ne "tc"} {error "entry mode not restored"}\n'
            script += "exit\n"
            (d / "fixture.tcl").write_text(script)
            p = subprocess.run([OPENROAD, "-no_init", "-exit", str(d / "fixture.tcl")],
                               capture_output=True, text=True, timeout=30)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr + "\n" + script)
            self.assertTrue((d / "after.rpt").is_file(), p.stdout + p.stderr)
            reports = [(d / (n + ".rpt")).read_text() for n in ("before", "during", "after")]
            self.assertEqual(reports[0], reports[2], "original timing paths/constraints not restored")
            if mm:
                self.assertEqual((d / "before.rpt.tc").read_text(), (d / "during.rpt.tc").read_text(),
                                 "TT setup changed while scoping FF repair")
            return reports

    def assert_nonport_paths(self, reports):
        before, during, _ = reports
        self.assertRegex(before, r"Startpoint: DIN\b")
        self.assertNotRegex(during, r"Startpoint: DIN\b")
        self.assertRegex(during, r"Endpoint: R2O\b")
        self.assertRegex(during, r"Startpoint: u_macro\b")
        self.assertRegex(during, r"Endpoint: u_macro_capture\b")

    def test_single_mode_nonport_real_paths(self):
        self.assert_nonport_paths(self.run_graph("nonport"))

    def test_multi_mode_nonport_real_paths(self):
        self.assert_nonport_paths(self.run_graph("nonport", mm=True))

    def test_multi_mode_repair_error_restores_real_paths(self):
        self.assert_nonport_paths(self.run_graph("nonport", mm=True, body_error=True))

    def test_legacy_reg2reg_still_excludes_outputs(self):
        _, during, _ = self.run_graph("reg2reg")
        self.assertNotRegex(during, r"Endpoint: R2O\b")
        self.assertRegex(during, r"Startpoint: u_macro\b")

    def test_default_keeps_all_paths(self):
        before, during, _ = self.run_graph(None)
        self.assertEqual(before, during)


if __name__ == "__main__":
    unittest.main()
