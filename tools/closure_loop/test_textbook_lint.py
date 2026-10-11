"""TEXTBOOK-LINT 2026-10-11: tools/textbook_lint.py checks and its closure-loop wiring."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
import closure_loop as cl  # noqa: E402
import textbook_lint as TL  # noqa: E402
from test_fp_lint import run_launch  # noqa: E402

TOOL = Path(__file__).resolve().parent.parent / "textbook_lint.py"


def netlist(n_ff=4, chain=2, port_fan=0, in2out=False, icg_port=False, out_levels=0):
    """clk -> n_ff flops in a ring through `chain` NAND2s; d_in -> 1 flop; optional port fan-out / in->out / ICG"""
    L = ["module top(clk, d_in, en, q_out, y_out);", "  input clk;", "  input d_in;", "  input en;", "  output q_out;",
         "  output y_out;"]
    for i in range(n_ff):
        prev = f"q{(i - 1) % n_ff}"
        x = prev
        for k in range(chain):
            L.append(f"  NAND2xp5_ASAP7_75t_R \\c{i}_{k}  (.A({x}), .B({x}), .Y(n{i}_{k}));")
            x = f"n{i}_{k}"
        L.append(f"  DFFHQNx1_ASAP7_75t_R \\r{i}$_DFF_P_  (.CLK(clk), .D({x}), .QN(q{i}));")
    L.append("  DFFHQNx1_ASAP7_75t_R \\rin  (.CLK(clk), .D(d_in), .QN(qin));")
    for i in range(port_fan):
        L.append(f"  AND2x2_ASAP7_75t_R \\pf{i}  (.A(en), .B(q0), .Y(pf{i}));")
        L.append(f"  DFFHQNx1_ASAP7_75t_R \\rpf{i}  (.CLK(clk), .D(pf{i}), .QN(qpf{i}));")
    x = "qin"
    for k in range(out_levels):
        L.append(f"  NOR2xp33_ASAP7_75t_R \\o{k}  (.A({x}), .B(q1), .Y(o{k}));")
        x = f"o{k}"
    L.append(f"  BUFx2_ASAP7_75t_R \\ob  (.A({x}), .Y(q_out));")
    L.append(f"  XOR2xp5_ASAP7_75t_R \\x  (.A({'d_in' if in2out else 'q1'}), .B(q2), .Y(y_out));")
    if icg_port:
        L.append("  ICGx1_ASAP7_75t_R \\cg  (.CLK(clk), .ENA(en), .SE(1'h0), .GCLK(gclk));")
        L.append("  DFFHQNx1_ASAP7_75t_R \\rg  (.CLK(gclk), .D(q0), .QN(qg));")
    L.append("endmodule")
    return "\n".join(L) + "\n"


def dump(pins=None, core=(0, 0, 100, 100)):
    def pin(name, x, y):
        return [name, name, "SIGNAL", "INPUT", [["M4", [x, y, x + 0.2, y + 0.02]]]]
    pins = pins or {"d_in": (0, 50), "q_out": (100, 50)}
    return {"die": list(core), "core": list(core), "masters": {}, "macros": [], "blockages": [],
            "bterms": [pin(n, *p) for n, p in pins.items()]}


def lint(text, d=None, **th):
    g, top = TL.flatten(TL.parse_verilog(text), None)
    res = TL.analyse(g, d if d is not None else dump(), dict(TL.THRESHOLDS, **th))
    return res


class Checks(unittest.TestCase):
    def test_clean_block(self):
        r = TL.verdict(lint(netlist()), "refuse")
        self.assertEqual(r["would_refuse"], [])
        self.assertEqual(r["flops"], 5)
        self.assertEqual(r["metrics"]["clock_roots"][0]["ff"], 5)

    def test_clock_root_tiers(self):
        r = lint(netlist(n_ff=30), clk_sinks_max=20, clk_sinks_refuse=1000)
        self.assertIn("clock_domain", r["findings"])
        self.assertNotIn("clock_domain", r["refuse"])
        r = lint(netlist(n_ff=30), clk_sinks_refuse=25)
        self.assertIn("clock_domain", r["refuse"])

    def test_port_fanout_and_constants(self):
        r = lint(netlist(port_fan=40), hf_report=32, hf_port_refuse=32)
        self.assertEqual(r["metrics"]["hf_max_port"], 40)
        self.assertIn("port en", r["refuse"]["high_fanout"][0])

    def test_boundary(self):
        r = lint(netlist(in2out=True))
        self.assertEqual(r["metrics"]["in_to_out_bits"], 1)
        self.assertIn("boundary", r["refuse"])
        r = lint(netlist(icg_port=True))
        self.assertEqual(r["metrics"]["icg_enable_from_port"], 1)
        self.assertIn("boundary", r["refuse"])
        r = lint(netlist(out_levels=5))
        self.assertEqual(r["metrics"]["reg_to_out_levels"], 5)
        self.assertIn("register->output 5 levels", r["refuse"]["boundary"][0])

    def test_depth(self):
        shallow = lint(netlist(chain=2))["metrics"]["depth_ps"]
        r = lint(netlist(chain=60))
        self.assertGreater(r["metrics"]["depth_ps"], 700)
        self.assertLess(shallow, 100)
        self.assertEqual(r["metrics"]["depth_levels"], 60)
        self.assertIn("logic_depth", r["refuse"])

    def test_wire_reach(self):
        # d_in -> rin -> (out_levels) -> q_out: one register between two pins 2 x 600 um apart
        d = dump({"d_in": (0, 0), "q_out": (1200, 0)}, core=(0, 0, 1200, 100))
        r = lint(netlist(), d)
        self.assertIn("wire_reach", r["refuse"])
        self.assertIn("rin", r["findings"]["wire_reach"][1])
        d = dump({"d_in": (0, 0), "q_out": (900, 0)}, core=(0, 0, 900, 100))
        self.assertNotIn("wire_reach", lint(netlist(), d)["refuse"])

    def test_util_is_warn_only(self):
        r = TL.verdict(lint(netlist()), "refuse")
        self.assertIn("util_channel", r["findings"])              # empty core -> util 0%
        self.assertNotIn("util_channel", r["refusing_checks"])

    def test_hierarchy_and_assign(self):
        text = ("module sub(a, y);\n input a;\n output y;\n INVx1_ASAP7_75t_R u (.A(a), .Y(y));\nendmodule\n"
                "module top(clk, d, q);\n input clk;\n input [1:0] d;\n output q;\n wire w;\n assign w = d[1];\n"
                " sub s0 (.a(w), .y(n));\n DFFHQNx1_ASAP7_75t_R r (.CLK(clk), .D(n), .QN(q));\nendmodule\n")
        g, top = TL.flatten(TL.parse_verilog(text), None)
        self.assertEqual(top, "top")
        self.assertEqual({c[0] for c in g.cells}, {"INVx1_ASAP7_75t_R", "DFFHQNx1_ASAP7_75t_R"})
        r = TL.analyse(g, None, TL.THRESHOLDS)
        self.assertEqual(r["metrics"]["in_to_reg_levels"], 0)

    def test_cli_modes_and_cfg(self):
        with tempfile.TemporaryDirectory() as td:
            n, d, c = Path(td, "n.v"), Path(td, "d.json"), Path(td, "c.json")
            n.write_text(netlist(in2out=True))
            d.write_text(json.dumps(dump()))
            run = lambda *a: subprocess.run([sys.executable, str(TOOL), "check", "--netlist", str(n), "--dump", str(d), *a],
                                            capture_output=True, text=True)
            p = run()
            self.assertEqual(p.returncode, 0)
            self.assertIn("WARN(refuse-tier) boundary", p.stdout)
            p = run("--mode", "refuse")
            self.assertEqual(p.returncode, 3)
            self.assertIn("TEXTBOOK_LINT: boundary", p.stdout)
            c.write_text(json.dumps({"mode": "refuse", "waive": ["boundary"]}))
            self.assertEqual(run("--cfg", str(c)).returncode, 0)
            c.write_text(json.dumps({"mode": "off"}))
            self.assertIn("disabled", run("--cfg", str(c)).stdout)


class LoopWiring(unittest.TestCase):
    def test_cfg_written_and_shipped(self):
        with patch.object(cl, "STATE", Path(tempfile.mkdtemp())):
            b = run_launch({})
            self.assertIn('textbook_cfg.json', b)
            self.assertIn('"mode": "warn"', b)
            (cl.STATE / "textbook_lint.json").write_text(json.dumps({"mode": "refuse"}))
            self.assertIn('"mode": "refuse"', run_launch({}))
            self.assertIn('"mode": "off"', run_launch({"textbook_lint": False}))
            self.assertIn('"waive": ["util_channel"]', run_launch({"textbook_lint": {"waive": ["util_channel"]}}))
        self.assertIn("../textbook_lint.py", cl.HELPERS)
        self.assertIn("textbook_lint.py; do", run_launch({}))

    def test_warn_logged_once(self):
        j = {"name": "t", "run": "/r", "host": "h", "stage_tag": "route.a1", "spec": {}}
        out = "textbook_lint: WARN top cells 10\ntextbook_lint: WARN boundary: x\n"
        calls = []

        def fake_ssh(host, c, **k):
            calls.append(c)
            return SimpleNamespace(returncode=0, stdout=out, stderr="")
        with patch.object(cl, "ssh", fake_ssh), patch.object(cl, "log", lambda m: None):
            cl.textbook_note(j)
            cl.textbook_note(j, force=True)
        self.assertEqual(len(calls), 1)
        self.assertIn("TEXTBOOK-LINT route.a1", j["events"][-1])
        self.assertIn("boundary: x", j["events"][-1])

    def test_refusal_finishes_floorplan_margin(self):
        j = {"name": "t", "run": "/r", "host": "ot-epyc3", "stage_tag": "route.a1", "attempt": 1, "retries_used": 0,
             "spec": {"verdict": {}}, "status": "RUNNING"}
        fail = "FLOORPLAN_MARGIN: textbook_lint: logic_depth: ~900 ps > 700 ps"
        done = {}

        def fake_ssh(host, c, **k):
            return SimpleNamespace(returncode=0, stdout=fail if "fplint/route.a1/FAIL" in c else "", stderr="")
        with patch.object(cl, "ssh", fake_ssh), patch.object(cl, "finish", lambda j, s, r, t: done.update(s=s, r=r)), \
                patch.object(cl, "kill_own_stage", lambda j: None):
            cl.crash(j, {"kind": "route", "key": "route"}, None, "rc=1")
        self.assertEqual(done["s"], "FLOORPLAN_MARGIN")
        self.assertTrue(done["r"].startswith("textbook_lint: logic_depth"))


if __name__ == "__main__":
    unittest.main()
