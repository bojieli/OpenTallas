"""face_land.py: port parsing (ANSI / non-ANSI), wrapper shape and spec completion (HKV-RSTCAP 10-19)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import face_land as F  # noqa: E402

ANSI = """module a_t #(parameter integer P=1)(input wire ck, input wire rst_n, input wire [7:0] d, e,
  output reg [3:0] q /* c */, output wire v); endmodule"""
NON = """module n_t(ck, rst_n, d, q);
  input ck; input rst_n; input [12:0] d; output [65:0] q;
  wire x; foo u (.input_like(x));
endmodule"""


class FaceLandTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / "rtl").mkdir()
        (self.d / "rtl/a.sv").write_text(ANSI)
        (self.d / "rtl/n.v").write_text(NON)

    def test_ports(self):
        self.assertEqual(F.ports(self.d / "rtl/a.sv", "a_t"),
                         [("input", "", "ck"), ("input", "", "rst_n"), ("input", "[7:0]", "d"), ("input", "[7:0]", "e"),
                          ("output", "[3:0]", "q"), ("output", "", "v")])
        self.assertEqual(F.ports(self.d / "rtl/n.v", "n_t"),
                         [("input", "", "ck"), ("input", "", "rst_n"), ("input", "[12:0]", "d"), ("output", "[65:0]", "q")])

    def test_apply(self):
        s = {"top": "a_t", "clock_port": "ck", "sources": ["rtl/a.sv"], "reset_ports": ["rst_n"],
             "face_land": {"core": "a_t", "core_src": "rtl/a.sv", "reset_ports": ["rst_n"], "land": {"d": 1}, "reason": "t"}}
        F.apply(s, root=self.d)
        self.assertEqual(s["top"], "a_t_fl")
        self.assertEqual(s["sources"][-3:], [F.RELAY, F.LAND, "rtl/lib/face_land/a_t_fl.sv"])
        w = (self.d / "rtl/lib/face_land/a_t_fl.sv").read_text()
        self.assertIn("ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_fl_rst_rst_n (.clk(ck)", w)
        self.assertIn("ot_pin_land #(.W(8), .LAT(1), .MUT((MUT / 2) % 2)) u_fl_land_d", w)
        self.assertIn(".e(e)", w)
        F.apply(dict(s, sources=list(s["sources"])), write=False, root=self.d)      # idempotent, not stale

    def test_rejects(self):
        base = {"top": "a_t", "clock_port": "ck", "sources": ["rtl/a.sv"], "reset_ports": ["rst_n"]}
        for fl in ({"reset_ports": ["d"]}, {"land": {"q": 1}}, {"land": {"rst_n": 1}}, {"land": {"d": 0}}, {}):
            with self.assertRaises(F.FaceLandError):
                F.apply(dict(base, face_land={"core": "a_t", "core_src": "rtl/a.sv", "reason": "t", **fl}), root=self.d)


if __name__ == "__main__":
    unittest.main()
