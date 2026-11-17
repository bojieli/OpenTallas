"""CTS-stage hold repair scope (HOLD-FLOW-R 11-16, COORD finding from FABLE-PD-QC-HEADSEG44).

The CTS repair runs in the 3_place.sdc stage of the two-mode session, the GRT repair in 4_cts.sdc.  Until now
ot_hold_repair_scope returned early at 3_place.sdc, so OT_HOLD_REPAIR_SCOPE / the reg2reg default never reached the CTS
repair: headseg44 put 16,494 hold BUFx2 into port paths there.  Fixture: 40 input ports each into a flop (port paths) and
two internal flop-to-flop paths.  repair_timing pads every hold endpoint it can see, so the endpoint count seen by
the repair body is the buffer count.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "die_plan/post_route_drv"))
import test_nonport_scope_sta as fixture  # noqa: E402

OPENROAD = os.environ.get("OPENROAD_BIN") or shutil.which("openroad")
NPORT = 40
NETLIST = ("module top(input CK, input [%d:0] DIN, output R2O);\nwire q0, q1;\n" % (NPORT - 1)
           + "".join(f"DFF u_in{i}(.CK(CK), .D(DIN[{i}]), .Q());\n" for i in range(NPORT))
           + "DFF u_a(.CK(CK), .D(DIN[0]), .Q(q0));\nDFF u_b(.CK(CK), .D(q0), .Q(q1));\nDFF u_c(.CK(CK), .D(q1), .Q(R2O));\nendmodule\n")


@unittest.skipUnless(OPENROAD, "OpenROAD required")
class CtsHoldScope(unittest.TestCase):
    def endpoints_seen(self, stage, scope="reg2reg", env=""):
        with tempfile.TemporaryDirectory(prefix="cts-hold-scope-") as td:
            d = Path(td)
            (d / "f.lib").write_text(fixture.LIB)
            (d / "f.lef").write_text(fixture.LEF)
            (d / "f.v").write_text(NETLIST)
            s = (f"read_lef {{{d}/f.lef}}\nread_liberty {{{d}/f.lib}}\nset_mode tc\nset_mode ff\n"
                 f"define_scene TC -mode tc -liberty {{{d}/f.lib}}\ndefine_scene BC -mode ff -liberty {{{d}/f.lib}}\n"
                 f"read_verilog {{{d}/f.v}}\nlink_design top\n")
            for mode in ("tc", "ff"):
                s += f"set_mode {mode}\ncreate_clock -name clk -period 0.833 [get_ports CK]\n"
                s += "set_input_delay -clock clk -min -0.02 [get_ports DIN*]\nset_input_delay -clock clk -max 0.1 [get_ports DIN*]\n"
                s += "set_output_delay -clock clk -min 0 [all_outputs]\nset_output_delay -clock clk -max 0.1 [all_outputs]\n"
            s += f"set ::env(RESULTS_DIR) {{{d}}}\nset_mode tc\nset ::ot_mm_active 1\nset ::ot_mm_synced 1\nset ::ot_mm_stage {stage}\n"
            s += "proc ot_hold_stats {} {return [sta::worst_slack_cmd min]}\n" + fixture.production_helper(True) + "\n"
            if scope is not None:
                s += f"set ::env(OT_HOLD_REPAIR_SCOPE) {{{scope}}}\n"
            s += env
            s += ("proc seen {} { set_scene BC; report_checks -path_delay min -scenes BC -group_path_count 1000 "
                  f"-endpoint_path_count 1 -unique_paths_to_endpoint > {{{d}/seen.rpt}} }}\n")
            s += "ot_hold_repair_scope { seen }\nexit\n"
            (d / "t.tcl").write_text(s)
            p = subprocess.run([OPENROAD, "-no_init", "-exit", str(d / "t.tcl")], capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            txt = (d / "seen.rpt").read_text()
            return sum(1 for ln in txt.splitlines() if ln.startswith("Endpoint:"))

    def test_cts_stage_repair_sees_internal_endpoints_only(self):
        cts = self.endpoints_seen("3_place.sdc")      # the CTS-stage repair
        grt = self.endpoints_seen("4_cts.sdc")        # the GRT-stage repair (already scoped)
        self.assertEqual(cts, grt, "CTS and GRT hold repair must see the same scoped endpoint set")
        self.assertEqual(cts, 2, f"CTS repair saw {cts} endpoints: port paths leak into it (40 port + 2 internal)")

    def test_scope_off_keeps_all_port_paths(self):
        allp = self.endpoints_seen("3_place.sdc", scope="")
        self.assertGreaterEqual(allp, NPORT, "opt-out (explicit empty scope) must keep the old all-path repair")

    def test_hold_pad_setting_runs_and_rejects_bad_cells(self):
        self.assertEqual(self.endpoints_seen("3_place.sdc", env="set ::env(OT_CTS_HOLD_PAD) HB2,HB4\n"), 2)
        with self.assertRaises(AssertionError):
            self.endpoints_seen("3_place.sdc", env="set ::env(OT_CTS_HOLD_PAD) HB9\n")

    def test_default_scope_is_reg2reg_at_cts(self):
        self.assertLessEqual(self.endpoints_seen("3_place.sdc", scope=None), 2)



class StaticWiring(unittest.TestCase):
    def test_scope_guard_accepts_the_cts_stage(self):
        txt = (HERE / "orfs_hold_mm.tcl").read_text()
        i = txt.index("proc ot_hold_repair_scope")
        self.assertIn("ni {3_place.sdc 4_cts.sdc}", txt[i:i + 2500])
        self.assertIn("unset_dont_use $pad", txt[i - 1500:i + 1500])


if __name__ == "__main__":
    unittest.main()
