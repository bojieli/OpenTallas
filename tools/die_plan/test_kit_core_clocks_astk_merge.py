"""ASTK-MERGE-1122: kit-rtl merges a core port from native pins that each carry an equal relay_depth chain."""
import pytest

import kit_core_clocks as K


def bound(depths=(2, 2), srcs=("r_q[0]", "r_q[0]")):
    st = []
    for pin, D, src in zip(("g_f__rst_n", "u_z__rst_n"), depths, srcs):
        sid = "astk_WN_" + pin.replace("__", "_")
        prev = src
        for s in range(D):
            q = f"lp_{sid}_0" if s == D - 1 else f"lp_{sid}_0_s{s}"
            st.append(f"    ot_dp_dly #(.W(1), .D(1)) u_y_xd_{sid}_0_{s} (.clk(clk), .d({prev}), .q({q}));")
            prev = q
    return ("module top (input wire clk);\n" + "\n".join(st) + "\n    kv3_astk u_astk_WN (\n"
            "        .ck(clk),\n        .g_f__rst_n(lp_astk_WN_g_f_rst_n_0[0]),\n        .u_z__rst_n(lp_astk_WN_u_z_rst_n_0[0])\n    );\nendmodule\n")


CORE = [dict(inst="astk_WN", module="kv3_astk", native_port_adapter=dict(merge={"g_f__rst_n": ["g_f__rst_n", "u_z__rst_n"]}))]


def test_equal_chains_merge_to_the_ports_own_chain():
    text, rec = K.adapt_core_ports(bound(), CORE)
    assert ".g_f__rst_n(lp_astk_WN_g_f_rst_n_0[0])" in text and "u_z__rst_n(" not in text


@pytest.mark.parametrize("kw", [dict(depths=(2, 3)), dict(srcs=("r_q[0]", "x_q[0]"))])
def test_unequal_chains_fail_closed(kw):
    with pytest.raises(ValueError, match="merge group is not one net"):
        K.adapt_core_ports(bound(**kw), CORE)
