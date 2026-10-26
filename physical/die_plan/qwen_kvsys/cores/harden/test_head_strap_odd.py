"""head_strap_odd.py: odd head_eighth strap master + substitution proof (TYPE-REDUCE-2 10-25)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import head_strap_odd as H  # noqa: E402


def core(e, bsel, hid="n1[1:0]"):
    a, b = H.LANES[e]
    return (f"// GENERATED kv3_head_eighth_e{e}\nmodule kv3_head_eighth_e{e} (\n"
            f"    input wire [0:0] g_t_{a}_u_l8__clk,\n    input wire [216:0] g_t_{a}_u_stin__dr_i,\n"
            f"    output wire [31:0] g_t_{b}_u_stk__kp_o\n);\n    wire [216:0] n1;   // w_head0_g_t_{a}_dr\n"
            f"    ot_qkh_lane8 u_g_t_{a}_u_l8 (\n        .bsel(2'b{bsel}),\n        .hid({hid}),\n"
            f"        .clk(g_t_{a}_u_l8__clk[0])\n    );\n    ot_qkh_lane8 u_g_t_{b}_u_l8 (\n        .bsel(2'b{bsel}),\n"
            f"        .clk(g_t_{a}_u_l8__clk[0])\n    );\nendmodule\n")


def test_master_adds_strap_port():
    m = H.master(core(1, "00"))
    assert "input wire [1:0] strap_bsel," in m and m.count(".bsel(strap_bsel)") == 2 and "2'b00" not in m


@pytest.mark.parametrize("m,e,v", [(1, 1, "00"), (1, 3, "01"), (5, 5, "10"), (5, 7, "11")])
def test_variant_is_master_with_strap_tied(m, e, v):
    assert H.proof(core(m, {1: "00", 5: "10"}[m]), core(e, v))


def test_wrong_logic_is_caught():
    assert not H.proof(core(1, "00"), core(3, "01", hid="n1[2:1]"))


def test_wrong_master_refused():
    with pytest.raises(SystemExit):
        H.proof(core(1, "00"), core(5, "10"))
    with pytest.raises(SystemExit):
        H.master(core(3, "01"))
