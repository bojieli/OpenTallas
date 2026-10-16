"""scalar_pin_view: x[0] -> x only for RTL-scalar ports; liberty bus wrapper removed; export lint (ROOT 2026-10-16)."""
import sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scalar_pin_view as S

LIB = '''library (x_tt) {
  type ("clk") {
    base_type : array;
    bit_width : 1;
    bit_from : 0;
    bit_to : 0;
  }
  type ("d") {
    base_type : array;
    bit_width : 2;
  }
  cell ("x") {
    bus("clk") {
      bus_type : clk;
      direction : input;
      capacitance : 0.0000;
    pin("clk[0]") {
      direction : input;
      clock : true;
    }
    }
    bus("d") {
      bus_type : d;
    pin("d[1]") {
      timing() { related_pin : "clk[0]"; }
    }
    pin("d[0]") {
      timing() { related_pin : "clk[0]"; when : "!xclk[0]"; }
    }
    }
  }
}
'''


class ScalarPinView(unittest.TestCase):
    def test_lib_rename(self):
        t = S.rename_lib(LIB, ["clk"])
        self.assertNotIn('type ("clk")', t)
        self.assertNotIn('bus("clk")', t)
        self.assertIn('pin("clk") {', t)
        self.assertEqual(t.count('related_pin : "clk"'), 2)
        self.assertIn('bus("d")', t)          # a real bus stays
        self.assertIn("xclk[0]", t)           # another name containing clk[0] is untouched

    def test_lef_and_json(self):
        lef = "MACRO x\n  PIN clk[0]\n    DIRECTION INPUT ;\n  END clk[0]\n  PIN sclk[0]\n  END sclk[0]\nEND x\n"
        t = S.rename_lef(lef, ["clk"])
        self.assertIn("PIN clk\n", t)
        self.assertIn("PIN sclk[0]", t)
        self.assertEqual(S.rename_json_text('{"a": "clk[0]", "b": "u/clk[0]", "c": "sclk[0]"}', ["clk"]),
                         '{"a": "clk", "b": "u/clk[0]", "c": "sclk[0]"}')

    def test_rtl_ranges_with_operators(self):
        d = Path(tempfile.mkdtemp())
        f = d / "m.sv"
        f.write_text("module m #(parameter integer T = 0) (\n input wire clk, rst_n,\n input wire [0:0] ck,\n"
                     " output wire [((T != 0) ? 4 : 1)-1:0] t_d,\n output reg v);\nendmodule\n")
        p = S.rtl_ports([f], "m")
        self.assertEqual({k: v["ranged"] for k, v in p.items()},
                         {"clk": False, "rst_n": False, "ck": True, "t_d": True, "v": False})

    def test_export_lint(self):
        d = Path(tempfile.mkdtemp())
        (d / "rtl.sv").write_text("module m (input wire clk, input wire [0:0] ck, output wire [3:0] q);\nendmodule\n")
        (d / "kit.env").write_text(f"TOP=m\nSRCS='{d / 'rtl.sv'}'\n")
        (d / "m.lef").write_text("MACRO m\n PIN clk[0]\n END clk[0]\n PIN ck[0]\n END ck[0]\n PIN q[0]\n END q[0]\nEND m\n")
        old = S.ROOT
        try:
            S.ROOT = Path("/")
            self.assertEqual(S.scalar_pin_lint(d / "m.lef", d, "m"), ["clk[0]"])
        finally:
            S.ROOT = old


if __name__ == "__main__":
    unittest.main()
