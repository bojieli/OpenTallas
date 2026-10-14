#!/usr/bin/env python3
"""Shared parts of the HROW ACK prototype (066ec43c5) taken centrally: define-aware port parsing and pre-flop pin hooks."""
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import pre_route_gate as PG  # noqa: E402
import ref_tile as RT  # noqa: E402

SRC = """module top (
  input  wire clk,
`ifdef CAND_ACK
  output wire ack_o,
`endif
  input  wire rst_n
);
`ifdef CAND_ACK
  assign ack_o = rst_n;
`endif
endmodule
"""


@unittest.skipUnless(shutil.which("iverilog"), "iverilog not installed")
class DefinePorts(unittest.TestCase):
    def test_defines_select_interface(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "t.sv").write_text(SRC)
            on = PG.rtl_ports(["t.sv"], "top", root=root, defines=["CAND_ACK"])
            off = PG.rtl_ports(["t.sv"], "top", root=root, defines=["OTHER"])
            self.assertIn("ack_o", on)
            self.assertNotIn("ack_o", off)
            for ports in (on, off):
                self.assertFalse(any("ifdef" in p or "endif" in p for p in ports), ports)

    def test_no_defines_is_the_plain_text_parse(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "t.sv").write_text(SRC.replace("`ifdef CAND_ACK\n  output wire ack_o,\n`endif\n", ""))
            self.assertEqual(set(PG.rtl_ports(["t.sv"], "top", root=root)), {"clk", "rst_n"})


class PinHookBeforeFlops(unittest.TestCase):
    BASE = dict(io_flop_at_pins=True, inhold=True, recipe=2)

    def test_hook_sourced_before_pin_flops_and_synced(self):
        hook = "physical/qwen_die_masters/io_flop_at_pins.tcl"   # any existing repo Tcl
        s = dict(self.BASE, pin_hook_before_flops=[hook], sources=[], route={}, kind="tile", clock="cts", macros=[], children=[])
        pre = RT.gen_pin_hooks(s)
        text = next(v for k, v in pre.items() if "gpl" in k.lower())
        lines = [ln for ln in text.splitlines() if ln.startswith("source ")]
        self.assertEqual(lines[-2], f"source /src/{hook}")
        self.assertTrue(lines[-1].endswith("io_flop_at_pins.tcl"))
        self.assertIn(hook, RT.referenced_paths(s, "kd"))

    def test_unsafe_or_missing_or_unwrapped_hooks_refused(self):
        for bad in ("/etc/x.tcl", "../x.tcl", "physical/none/missing.tcl", "a b.tcl"):
            with self.assertRaises(RT.SpecError):
                RT.gen_pin_hooks(dict(self.BASE, pin_hook_before_flops=[bad]))
        with self.assertRaises(RT.SpecError):
            RT.gen_pin_hooks(dict(pin_hook_before_flops=["physical/qwen_die_masters/io_flop_at_pins.tcl"]))


if __name__ == "__main__":
    unittest.main()
