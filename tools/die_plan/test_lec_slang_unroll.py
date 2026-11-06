"""Finite Slang elaboration budgets do not change RTL or proof assumptions."""
import argparse
import importlib.util
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("lec", Path(__file__).with_name("lec.py"))
lec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lec)
KEY = "OT_LEC_SLANG_UNROLL_LIMIT"


class SlangUnrollTests(unittest.TestCase):
    def test_absent_preserves_frontend_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(lec.slang_unroll_args({}), [])

    def test_explicit_budget_and_captured_kit_priority(self):
        with patch.dict(os.environ, {KEY: "4104"}, clear=True):
            self.assertEqual(lec.slang_unroll_args({}), ["--unroll-limit=4104"])
            self.assertEqual(lec.slang_unroll_args({KEY: "32912"}), ["--unroll-limit=32912"])

    def test_zero_unlimited_negative_and_invalid_rejected(self):
        with patch.dict(os.environ, {}, clear=True):
            for value in ("0", "-1", "unlimited", "2.5", "1 --ignore-assertions", ""):
                with self.subTest(value=value), self.assertRaises(lec.LecError):
                    lec.slang_unroll_args({KEY: value})

    def test_async_identity_captures_kit_elaboration_budget(self):
        shell = Path(__file__).with_name("lec_async.sh").read_text()
        function = shell[shell.index("identity() {"):shell.index("bootstrap() {")]
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {}, clear=True):
            kit = Path(d)
            (kit / "rtl").mkdir()
            (kit / "rtl/top.sv").write_text("module top; endmodule")
            (kit / "lec.py").write_text("# same proof driver")
            def identity(limit, prefix="export "):
                (kit / "config.mk").write_text("export DESIGN_NAME = top\nexport VERILOG_FILES = /work/rtl/top.sv\n"
                                               f"{prefix}{KEY} = {limit}\n")
                return subprocess.check_output(["/bin/bash", "-c", function + '\nidentity "$1" source', "probe", d],
                                               text=True).strip()
            self.assertNotEqual(identity(32912), identity(32913))
            self.assertNotEqual(identity(32912, ""), identity(32913, ""))

    def test_host_frontend_option_reaches_container(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {KEY: "32912"}, clear=True):
            args = argparse.Namespace(kit=d, out=str(Path(d) / "out"), conflicts=100, jobs=1,
                                      netlist=None, reuse=False, gold_frontend=None, hints=None, port_map=None)
            with patch.object(lec.subprocess, "run") as run:
                run.return_value.returncode = 0
                self.assertEqual(lec.via_docker(args, "pinned-image", 16), 0)
            self.assertIn("OT_LEC_SLANG_UNROLL_LIMIT=32912", run.call_args.args[0])

    def test_slang_only_and_no_reset_or_source_changes(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {}, clear=True):
            source = Path(d) / "top.sv"
            text = "module top(input clk,d,output reg q); always @(posedge clk) q<=d; endmodule\n"
            source.write_text(text)
            env = {"DESIGN_NAME": "top", "VERILOG_FILES": "top.sv"}
            with patch.object(lec, "rtl_standard_libs", return_value=[]):
                ordinary = lec.read_rtl_cmds(env, d, "slang", [])
                selected = lec.read_rtl_cmds(dict(env, **{KEY: "32912"}), d, "slang", [])
                self.assertEqual([x.replace(" --unroll-limit=32912", "") for x in selected], ordinary)
                self.assertEqual(lec.read_rtl_cmds(env, d, "verilog", []),
                                 lec.read_rtl_cmds(dict(env, **{KEY: "32912"}), d, "verilog", []))
            self.assertEqual(source.read_text(), text)


if __name__ == "__main__":
    unittest.main()
