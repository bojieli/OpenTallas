"""AUTOBUILD-PIPE-4 10-31 (OWNER 12.27 d): generation-time kit lint, static parts (the yosys part runs in the flow
image; its parsers are tested here on the yosys text)."""
import os
import sys
from unittest import mock
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
        with mock.patch.dict(os.environ, {"OT_LINT_MEMORY_MAX_BITS": "0"}):      # 0 = recipe bound only
            e = GL.memory_errors(rows, {"SYNTH_MEMORY_MAX_BITS": ["8192"]})
            self.assertEqual(len(e), 1)
            self.assertIn("8224 bits > SYNTH_MEMORY_MAX_BITS 8192", e[0])
            self.assertEqual(GL.memory_errors(rows, {"SYNTH_MEMORY_MAX_BITS": ["16384"]}), [])
            self.assertEqual(len(GL.memory_errors(rows, {})), 1)                # ORFS default 4096
        self.assertEqual(GL.memory_errors(rows, {"SYNTH_MOCK_LARGE_MEMORIES": ["1"]}), [])

    def test_memory_bits_lint_override(self):
        """FAIL-S81-1 11-14: OT_LINT_MEMORY_MAX_BITS (default 65536) raises, never lowers, the lint bound"""
        big = [("m", 160, 265)]                                                  # 42400 bits
        env = {k: v for k, v in os.environ.items() if k != "OT_LINT_MEMORY_MAX_BITS"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(GL.memory_errors(big, {"SYNTH_MEMORY_MAX_BITS": ["16384"]}), [])
            self.assertEqual(len(GL.memory_errors([("m", 400, 400)], {"SYNTH_MEMORY_MAX_BITS": ["16384"]})), 1)
        with mock.patch.dict(os.environ, {"OT_LINT_MEMORY_MAX_BITS": "1"}):
            self.assertEqual(GL.memory_errors(big, {"SYNTH_MEMORY_MAX_BITS": ["65536"]}), [])
            self.assertEqual(len(GL.memory_errors(big, {"SYNTH_MEMORY_MAX_BITS": ["8192"]})), 1)
        with mock.patch.dict(os.environ, {"OT_LINT_MEMORY_MAX_BITS": "200000"}):
            self.assertEqual(GL.memory_errors([("m", 400, 400)], {"SYNTH_MEMORY_MAX_BITS": ["16384"]}), [])


if __name__ == "__main__":
    unittest.main()


def _git(d, *a):
    import subprocess
    return subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True, text=True).stdout.strip()


def test_src_skew_same_older_unknown(tmp_path, capsys):
    """AUTOBUILD-PIPE-5 (COORD 04:0x): kit src older than the queue lint fails only when a queue-lint file differs."""
    r = tmp_path / "repo"
    (r / "tools/die_plan").mkdir(parents=True)
    _git(tmp_path, "init", "-q", str(r))
    _git(r, "config", "user.email", "t@t"); _git(r, "config", "user.name", "t")
    (r / "tools/die_plan/sdc_lint.py").write_text("W = 356.5\n")
    (r / "tools/die_plan/gen_phys.py").write_text("x = 1\n")
    _git(r, "add", "-A"); _git(r, "commit", "-q", "-m", "a")
    a = _git(r, "rev-parse", "HEAD")
    (r / "tools/die_plan/gen_phys.py").write_text("x = 2\n")          # not a queue-lint file
    _git(r, "commit", "-q", "-am", "b")
    b = _git(r, "rev-parse", "HEAD")
    assert GL.src_skew(b, r)[0] == []                          # same commit
    assert GL.src_skew(a, r)[0] == []                          # older, but the queue lint is unchanged
    (r / "tools/die_plan/sdc_lint.py").write_text("W = 416.5\n")
    _git(r, "commit", "-q", "-am", "c")
    errs, info = GL.src_skew(a, r)
    assert len(errs) == 1 and "older than the queue lint" in errs[0] and info["differ"] == ["tools/die_plan/sdc_lint.py"]
    errs, info = GL.src_skew("0123456789ab", r)                # unknown commit: never a false fail
    assert "KW_SRC_SKEW_ERROR commit 0123456789ab" in capsys.readouterr().out
    assert errs == [] and info["applies"] is False
    assert GL.src_skew("", r)[0] == []


def test_landing_ff_lint_maps_only_when_the_kit_sets_it():
    """AUTOBUILD-PIPE-5 (COORD 06:1x, S81 iqf__t1): OT_LANDING_FF = 1 -> the lint maps the landing rings to flops
    exactly as ot_keep_regs.tcl does before memory_collect; otherwise the script is the unchanged LINT_TCL."""
    assert GL.lint_tcl({"DESIGN_NAME": ["top"]}) == GL.LINT_TCL.replace("@LANDING_FF@", "")
    on = GL.lint_tcl({"DESIGN_NAME": ["top"], "OT_LANDING_FF": ["1"]})
    assert on.index("yosys memory_map {*}{@ot_lf}") < on.index("memory_collect")
    assert "*ot_dp_clk_landing*" in on and "yosys hierarchy -top top" in on
    assert "@" + "LANDING_FF@" not in on


def test_platform_liberty_tcl_reads_libs_inside_image(tmp_path):
    """KIT-WAVE-8 10-31: platform liberties are globbed in the flow image, not on the host that writes the script."""
    (tmp_path / "config.mk").write_text("export DESIGN_NAME = demo\nexport VERILOG_FILES = /work/demo.sv\n")
    (tmp_path / "demo.sv").write_text("module demo(input a, output y);\n"
                                      "  (* keep *) HB4xp67_ASAP7_75t_R u_hb (.A(a), .Y(y));\nendmodule\n")
    pre = GL.platform_liberty_tcl(tmp_path, "read_verilog -defer -sv /work/demo.sv\n")
    assert "asap7sc7p5t_*_RVT_TT_nldm_*.lib*" in pre and "lrange" not in pre and "read_liberty -lib" in pre
    assert GL.platform_liberty_tcl(tmp_path, "read_liberty -lib /OpenROAD-flow-scripts/x.lib\n") == ""
    (tmp_path / "demo.sv").write_text("module demo(input a, output y); assign y = a; endmodule\n")
    pre = GL.platform_liberty_tcl(tmp_path, "")
    assert "SEQ_RVT_TT" in pre and "INVBUF_RVT_TT" in pre and pre.count("lrange $L 0 0") == 2


def test_gen_lint_rechecks_flattened_only_on_undriven(tmp_path, monkeypatch=None):
    """DIE-QC-61 11-01: undriven-only check problems -> one flattened re-check at >= FLAT_MEM_GB; other problems or a
    kit that already lints flattened -> no re-check."""
    (tmp_path / "config.mk").write_text("export DESIGN_NAME = demo\nexport VERILOG_FILES = /work/demo.sv\n")
    und = ["Warning: Wire $paramod$x\\part.\\x_addr [95] is used but has no driver."]
    calls = []

    def fake(answers):
        def run(kd, image, mem_gb, flatten):
            calls.append((mem_gb, flatten))
            return answers[len(calls) - 1]
        return run

    orig = GL._run_yosys
    try:
        GL._run_yosys = fake([(und, [], 0), ([], [], 0)])
        assert GL.run_yosys(tmp_path, mem_gb=8) == ([], [], 0)
        assert calls == [(8, None), (GL.FLAT_MEM_GB, True)]
        calls.clear()
        loop = ["Warning: found logic loop in module demo:"]
        GL._run_yosys = fake([(und + loop, [], 0)])
        assert GL.run_yosys(tmp_path, mem_gb=8)[0] == und + loop and calls == [(8, None)]
        calls.clear()
        (tmp_path / "config.mk").write_text("export DESIGN_NAME = demo\nexport VERILOG_FILES = /work/demo.sv\n"
                                            "export OT_RTL_LINT_FLATTEN = 1\n")
        GL._run_yosys = fake([(und, [], 0)])
        assert GL.run_yosys(tmp_path, mem_gb=8)[0] == und and calls == [(8, None)]
    finally:
        GL._run_yosys = orig


def test_src_skew_every_git_call_no_lazy_fetch(tmp_path, monkeypatch):
    seen = []
    real = GL.subprocess.run
    def fake(cmd, **kw):
        if cmd[:1] == ["git"]:
            seen.append(cmd)
            assert kw.get("env", {}).get("GIT_NO_LAZY_FETCH") == "1", cmd
        return real(cmd, **kw)
    monkeypatch.setattr(GL.subprocess, "run", fake)
    r = tmp_path / "r"
    r.mkdir()
    GL.subprocess.run.__wrapped__ = real
    real(["git", "init", "-q", str(r)], check=True)
    real(["git", "-C", str(r), "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "--allow-empty", "-m", "x"], check=True)
    head = real(["git", "-C", str(r), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    GL.src_skew(head, r)
    GL.src_skew("0123456789ab", r)
    assert len(seen) >= 2
