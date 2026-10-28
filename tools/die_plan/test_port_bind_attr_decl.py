"""DIE-HEAD-7 10-28 (RM92 gate): nested_check resolves wires declared with a leading attribute ((* keep = 1 *) wire
rst_n_t<k>; the TILEIO local reset consumers u_rrl_<k> (ot_dp_rgate).q) and still catches width mismatches on them."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import port_bind_gate as PBG  # noqa: E402

SRC = "module leaf (input wire clk, input wire d, output reg q);\nendmodule\n"


def _wr(decl):
    return {"w.sv": "module w (\n    input wire clk,\n    input wire d\n);\n" + decl +
            "    leaf u_l (.clk(clk), .d(d), .q(x));\nendmodule\n"}


def test_attribute_declared_wire_resolves():
    r = PBG.nested_check(_wr("    (* keep = 1 *) wire x;\n"), [SRC])
    assert r["verdict"] == "PASS", r


def test_attribute_declared_wire_width_still_checked():
    r = PBG.nested_check(_wr("    (* keep = 1 *) wire [1:0] x;\n"), [SRC])
    assert r["verdict"] == "FAIL" and r["width_mismatch"] == 1, r
