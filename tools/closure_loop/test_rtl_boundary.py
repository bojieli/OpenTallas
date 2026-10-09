"""struct-close 2026-10-09: rtl_boundary.py (submit-time registered-boundary check) and its submit_lint wiring."""
import os
import sys
import tempfile
import unittest
import copy
import hashlib
import json
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ["CL_STATE"] = tempfile.mkdtemp(prefix="rtlb_state_")
import rtl_boundary as B  # noqa: E402
import submit_lint as S  # noqa: E402

COMB = """module t_comb(input wire clk, input wire [7:0] a, input wire [7:0] b, output wire [7:0] y, output reg [7:0] q);
  assign y = a + b;
  always @(posedge clk) q <= a ^ b;
endmodule
"""
REG = """module t_reg(input wire clk, input wire rst_n, input wire [7:0] a, output reg [7:0] q);
  reg [7:0] a_q;
  always @(posedge clk or negedge rst_n) if (!rst_n) a_q <= 0; else a_q <= a;
  always @(posedge clk) q <= a_q + 8'd1;
endmodule
"""


def spec(top, path, **kw):
    s = {"name": "t", "source": {"commit": "c0ffee"}, "stages": {"route": {"cmd":
         f"OUT=x bash physical/hbm_mtp/route_mtp.sh {{LABEL}} {top} --source {path} --clock-port clk"}}}
    s.update(kw)
    return s


def show_for(files):
    return lambda commit, path: files.get(path)


def probe(*args, **kwargs):
    return B.check(*args, mode="probe", **kwargs)


class Boundary(unittest.TestCase):
    def test_comb_path_warns(self):
        r = probe(spec("t_comb", "rtl/t.sv"), show_for({"rtl/t.sv": COMB}))
        self.assertEqual(r["verdict"], "WARN")
        self.assertEqual(r["in_to_out_bits"], 8)

    def test_comb_path_refused_when_registered_io(self):
        r = probe(spec("t_comb", "rtl/t.sv", registered_io=True), show_for({"rtl/t.sv": COMB}))
        self.assertEqual(r["verdict"], "REFUSE")

    def test_registered_passes(self):
        r = probe(spec("t_reg", "rtl/r.sv", registered_io=True), show_for({"rtl/r.sv": REG}))
        self.assertEqual(r["verdict"], "PASS", r)
        self.assertEqual(r["in_to_reg_max"], 0)
        self.assertIn("rst_n", r["ctrl_ports"])

    def test_cl_spec_refused_by_default(self):
        r = probe(spec("t_comb", "rtl/t.sv", name="x-tc-cl"), show_for({"rtl/t.sv": COMB}))
        self.assertEqual(r["verdict"], "REFUSE")
        r = probe(spec("t_comb", "rtl/t.sv", name="x-tc-cl", rtl_boundary={"waive": "immediate-drop ready by design"}),
                    show_for({"rtl/t.sv": COMB}))
        self.assertEqual(r["verdict"], "WARN")
        r = probe(spec("t_comb", "rtl/t.sv", name="x-tc-cx", registered_io=False), show_for({"rtl/t.sv": COMB}))
        self.assertEqual(r["verdict"], "WARN")

    def test_unreadable_recipe_skips(self):
        r = probe({"source": {"commit": "c"}, "stages": {"route": {"cmd": "bash other.sh x"}}}, show_for({}))
        self.assertEqual(r["verdict"], "SKIP")

    def test_submit_lint_refuses_and_warns(self):
        class G:
            def __init__(self, f): self.f = f
            def show(self, c, p): return self.f.get(p)
            def blob(self, c, p): return "x"
        r = S.check(spec("t_comb", "rtl/t.sv", registered_io=True), G({"rtl/t.sv": COMB}), boundary_mode="probe")
        self.assertEqual(r["verdict"], "REFUSE")
        self.assertIn("rtl_boundary", r["message"])
        r = S.check(spec("t_comb", "rtl/t.sv"), G({"rtl/t.sv": COMB}), boundary_mode="probe")
        self.assertEqual(r["verdict"], "PASS")
        self.assertIn("WARN rtl_boundary", r["message"])

    def test_remote_probe_then_metadata_cache_only(self):
        with tempfile.TemporaryDirectory() as td, patch.object(B, "CACHE", Path(td) / "cache.json"):
            s = spec("t_reg", "rtl/r.sv", registered_io=True)
            show = show_for({"rtl/r.sv": REG})
            # This test must run on an admitted remote host: real Yosys creates proof.
            self.assertEqual(probe(s, show)["verdict"], "PASS")
            with patch.object(B.subprocess, "run", side_effect=AssertionError("metadata launched subprocess")):
                r = B.check(s, show)
                self.assertEqual(r["verdict"], "PASS")
                self.assertTrue(r["cached"])
                for field in ("commit", "recipe", "levels"):
                    stale = copy.deepcopy(s)
                    if field == "commit": stale["source"]["commit"] = "other"
                    elif field == "recipe": stale["stages"]["route"]["cmd"] += " --param N=2"
                    else: stale["rtl_boundary"] = {"levels": 15}
                    with self.subTest(stale=field):
                        self.assertEqual(B.check(stale, show)["verdict"], "REFUSE")
                B.CACHE.unlink()
                self.assertEqual(B.check(s, show)["verdict"], "REFUSE")
                key = hashlib.sha256(json.dumps([s["source"]["commit"], B.recipe(s, show), B.LEVELS],
                                               sort_keys=True).encode()).hexdigest()[:24]
                B.CACHE.write_text(json.dumps({key: {"verdict": "PASS"}}))
                self.assertEqual(B.check(s, show)["verdict"], "REFUSE")

    def test_submit_missing_proof_refuses_without_probe(self):
        class G:
            def show(self, c, p): return {"rtl/r.sv": REG}.get(p)
            def blob(self, c, p): return "x"
        with tempfile.TemporaryDirectory() as td, patch.object(B, "CACHE", Path(td) / "absent.json"), \
                patch.object(B.subprocess, "run", side_effect=AssertionError("metadata launched subprocess")):
            r = S.check(spec("t_reg", "rtl/r.sv"), G())
            self.assertEqual(r["verdict"], "REFUSE")
            self.assertIn("missing source-bound proof", r["message"])


if __name__ == "__main__":
    unittest.main()
