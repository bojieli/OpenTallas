"""AUTOBUILD-PIPE-4 10-31 (OWNER 12.27 d): generation-time kit lint, static parts (the yosys part runs in the flow
image; its parsers are tested here on the yosys text)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_gen_lint as GL  # noqa: E402

TIE = """set cland_block [ord::get_db_block]
set cland_net [$cland_src getNet]
$cland_dst disconnect
$cland_dst connect $cland_net
$cland_net setSigType CLOCK
puts {OT_CLAND_EXPORT fclk_out_cland_up <- clk}
"""
FWD = TIE.replace("$cland_dst connect $cland_net", "$cland_dst connect $cland_fn").replace(
    "<- clk}", "<- clk via cland_fwd_fclk_out_cland_up (BUFx24_ASAP7_75t_R at the source)}")
SDC = "create_clock -name clk -period 1000 [get_ports clk]\n" \
      "create_generated_clock -name fclk_out_cland_up -source [get_ports clk] -divide_by 1 [get_ports fclk_out_cland_up]\n"


def kit(files):
    d = Path(tempfile.mkdtemp())
    for name, text in files.items():
        (d / name).parent.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(text)
    return d


class ClockExportForm(unittest.TestCase):
    def test_tie_form_with_generated_clock_fails(self):
        errs, applies = GL.clock_export_form(kit({"landing_exports.tcl": TIE, "constraint.sdc": SDC}))
        self.assertTrue(applies)
        self.assertEqual(len(errs), 1)
        self.assertIn("fclk_out_cland_up", errs[0])
        self.assertIn("CTS-0114", errs[0])

    def test_fwd_buffer_form_passes(self):
        self.assertEqual(GL.clock_export_form(kit({"landing_exports.tcl": FWD, "constraint.sdc": SDC})), ([], True))

    def test_no_exports_is_na(self):
        self.assertEqual(GL.clock_export_form(kit({"constraint.sdc": SDC})), ([], False))


class MacroTcl(unittest.TestCase):
    LEF = "MACRO ot_sram_x\n  SIZE 10 BY 20 ;\nEND ot_sram_x\n"
    RTL = "module top(input clk); ot_sram_x u_m (.clk(clk)); endmodule\n"

    def cfg(self, extra=""):
        return ("export DESIGN_NAME = top\nexport VERILOG_FILES = /work/rtl/top.v\n"
                "export ADDITIONAL_LEFS = /work/macros/ot_sram_x.lef\n" + extra)

    def test_instantiated_macro_without_placement_tcl_fails(self):
        d = kit({"config.mk": self.cfg(), "rtl/top.v": self.RTL, "macros/ot_sram_x.lef": self.LEF})
        errs, applies = GL.macro_tcl(d)
        self.assertTrue(applies)
        self.assertIn("no staged MACRO_PLACEMENT_TCL", errs[0])

    def test_staged_placement_tcl_passes(self):
        d = kit({"config.mk": self.cfg("export MACRO_PLACEMENT_TCL = /work/macro_place.tcl\n"), "rtl/top.v": self.RTL,
                 "macros/ot_sram_x.lef": self.LEF, "macro_place.tcl": "place_macro -macro_name u_m -location {1 1}\n"})
        self.assertEqual(GL.macro_tcl(d), ([], True))

    def test_macro_not_instantiated_is_na(self):
        d = kit({"config.mk": self.cfg(), "rtl/top.v": "module top(input clk); endmodule\n",
                 "macros/ot_sram_x.lef": self.LEF})
        self.assertEqual(GL.macro_tcl(d), ([], False))


class YosysParsers(unittest.TestCase):
    LOG = ("6. Executing CHECK pass (checking for obvious problems).\nChecking module t...\n"
           "Warning: multiple conflicting drivers for t.\\z:\n    module input a[0]\n"
           "Warning: Wire t.\\y is used but has no driver.\nFound and reported 2 problems.\n")

    def test_check_problems(self):
        p = GL.parse_check(self.LOG)
        self.assertEqual(len(p), 2)
        self.assertIn("multiple conflicting drivers", p[0])
        self.assertEqual(GL.parse_check("Found and reported 0 problems.\n"), [])

    def test_memory_bits_vs_limit(self):
        rows = [("qkd_hr_cdc_hi/u_hx.mem", 514, 16), ("t/small", 8, 16)]
        e = GL.memory_errors(rows, {"SYNTH_MEMORY_MAX_BITS": ["8192"]})
        self.assertEqual(len(e), 1)
        self.assertIn("8224 bits > SYNTH_MEMORY_MAX_BITS 8192", e[0])
        self.assertEqual(GL.memory_errors(rows, {"SYNTH_MEMORY_MAX_BITS": ["16384"]}), [])
        self.assertEqual(len(GL.memory_errors(rows, {})), 1)            # ORFS default 4096
        self.assertEqual(GL.memory_errors(rows, {"SYNTH_MOCK_LARGE_MEMORIES": ["1"]}), [])


if __name__ == "__main__":
    unittest.main()
