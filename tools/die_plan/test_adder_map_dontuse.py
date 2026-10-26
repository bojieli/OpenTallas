#!/usr/bin/env python3
"""unit tests: tools/die_plan/adder_map_dontuse.py (python3 -m pytest tools/die_plan/test_adder_map_dontuse.py)"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adder_map_dontuse as A  # noqa: E402

# the asap7 platform map shape (openroad/orfs:asap7lock platforms/asap7/yoSys/cells_adders_R.v, abridged)
MAP = """(* techmap_celltype = "$fa" *)
module _tech_fa (A, B, C, X, Y);
  parameter WIDTH = 1;
  input [WIDTH-1 : 0] A, B, C;
  output [WIDTH-1 : 0] X, Y;
  wire [WIDTH-1 : 0] NX, NY;
  genvar i;
  generate for (i = 0; i < WIDTH; i = i + 1) begin
      if (_TECHMAP_CONSTVAL_C_[i] === 1'b0) begin
          HAxp5_ASAP7_75t_R halfadder_Cconst (
              .A(A[i]),
              .B(B[i]),
              .CON(NX[i]), .SN(NY[i])
            );
      end else begin
        FAx1_ASAP7_75t_R fulladder (
            .A(A[i]), .B(B[i]), .CI(C[i]), .CON(NX[i]), .SN(NY[i])
          );
      end
      assign X[i] = ~NX[i];
      assign Y[i] = ~NY[i];
  end endgenerate
endmodule
"""
CFG = """export DONT_USE_CELLS          = *x1p*_ASAP7* *xp*_ASAP7*
export DONT_USE_CELLS          += SDF* ICG*
"""


class T(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "yoSys").mkdir()
        (self.d / "yoSys" / "cells_adders_R.v").write_text(MAP)
        (self.d / "config.mk").write_text(CFG)

    def test_patterns(self):
        self.assertEqual(A.dont_use_patterns(self.d / "config.mk"), ["*x1p*_ASAP7*", "*xp*_ASAP7*", "SDF*", "ICG*"])
        self.assertTrue(A.is_dont_use("HAxp5_ASAP7_75t_R", A.dont_use_patterns(self.d / "config.mk")))
        self.assertFalse(A.is_dont_use("FAx1_ASAP7_75t_R", A.dont_use_patterns(self.d / "config.mk")))

    def test_gen_replaces_haxp5_keeps_fa(self):
        out = self.d / "m.v"
        rc = A.main(["gen", "--platform-dir", str(self.d), "--out", str(out), "--report", str(self.d / "r.json")])
        self.assertEqual(rc, 0)
        t = out.read_text()
        self.assertNotIn("HAxp5_ASAP7_75t_R halfadder", t)
        self.assertIn("FAx1_ASAP7_75t_R fulladder", t)
        self.assertIn("assign NX[i] = ~((A[i]) & (B[i]));", t)
        self.assertIn("assign NY[i] = ~((A[i]) ^ (B[i]));", t)
        r = json.loads((self.d / "r.json").read_text())
        self.assertEqual(r["verdict"], "PASS")
        self.assertEqual([x["cell"] for x in r["replaced"]], ["HAxp5_ASAP7_75t_R"])
        self.assertEqual(r["cells_kept"], ["FAx1_ASAP7_75t_R"])

    def test_gen_fails_on_unknown_dont_use(self):
        (self.d / "yoSys" / "cells_adders_R.v").write_text(MAP.replace(
            "FAx1_ASAP7_75t_R fulladder", "FAxp33_ASAP7_75t_R fulladder"))
        rc = A.main(["gen", "--platform-dir", str(self.d), "--out", str(self.d / "m.v")])
        self.assertEqual(rc, 1)
        self.assertFalse((self.d / "m.v").exists())

    def test_check(self):
        good = self.d / "good.v"
        good.write_text("module t(a,b,y);\n  FAx1_ASAP7_75t_R _1_ (.A(a), .B(b), .CI(c), .CON(x), .SN(y));\nendmodule\n")
        bad = self.d / "bad.v"
        bad.write_text("module t(a,b,y);\n  HAxp5_ASAP7_75t_R _5023_ (\n    .A(a),\n    .B(b),\n    .CON(x),\n"
                       "    .SN(y)\n  );\n  DFFHQNx1_ASAP7_75t_R r (.CLK(c), .D(y), .QN(q));\nendmodule\n")
        self.assertEqual(A.main(["check", "--platform-dir", str(self.d), "--netlist", str(good)]), 0)
        self.assertEqual(A.main(["check", "--platform-dir", str(self.d), "--netlist", str(bad),
                                 "--report", str(self.d / "c.json")]), 1)
        self.assertEqual(json.loads((self.d / "c.json").read_text())["dont_use_cells"], {"HAxp5_ASAP7_75t_R": 1})


if __name__ == "__main__":
    unittest.main()
