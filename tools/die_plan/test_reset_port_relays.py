"""reset.port_relays: opt-in relays from the delivered reset to named ot_dp_st sinks, fail closed."""
import pytest
import reset_port_relays as R

TXT = """module m (
    input  wire clk,
    input  wire arst_n,
    input  wire [1:0] a,
    output wire [1:0] b
);
    wire a_q, a_eq;
    wire rst_n = arst_n;  // delivered reset to the native hard partition
    ot_dp_st #(.W(1)) u_bin_a (.clk(clk), .rst_n(rst_n), .d(a[0:0]), .ea(a[1]), .q(a_q), .eq(a_eq));
    ot_dp_st #(.W(1)) u_bout_b (.clk(clk), .rst_n(rst_n), .d(a_q), .ea(rst_n), .q(b[0:0]), .eq(b[1]));
endmodule
"""


def test_empty_is_identity():
    assert R.apply(TXT, []) == (TXT, [])


def test_chain_and_only_named_sink_moves():
    out, rec = R.apply(TXT, [dict(name="h", depth=2, sinks=["u_bin_a"])])
    assert "ot_dp_rrelay u_prl_h_0 (.clk(clk), .d(rst_n), .q(prl_h_0));" in out
    assert "ot_dp_rrelay u_prl_h_1 (.clk(clk), .d(prl_h_0), .q(prl_h_1));" in out
    assert "u_bin_a (.clk(clk), .rst_n(prl_h_1)," in out
    # the other face register and the out epoch source keep the delivered reset
    assert "u_bout_b (.clk(clk), .rst_n(rst_n), .d(a_q), .ea(rst_n)," in out
    assert rec == [dict(name="h", depth=2, relays=["u_prl_h_0", "u_prl_h_1"], sinks=["u_bin_a"], reset="prl_h_1")]
    assert out.index("wire rst_n = arst_n;") < out.index("u_prl_h_0")


@pytest.mark.parametrize("rows,msg", [
    ([dict(name="h", depth=2, sinks=["u_nope"])], "not an emitted ot_dp_st"),
    ([dict(name="h", depth=0, sinks=["u_bin_a"])], "depth"),
    ([dict(name="h", depth=1, sinks=["u_bin_a"]), dict(name="h", depth=1, sinks=["u_bout_b"])], "duplicate relay name"),
    ([dict(name="h", depth=1, sinks=["u_bin_a", "u_bin_a"])], "duplicate sink"),
    ([dict(name="h", depth=1, sinks=["u_bin_a"], extra=1)], "exactly name, depth, sinks"),
])
def test_fail_closed(rows, msg):
    with pytest.raises(R.PortRelayError, match=msg):
        R.apply(TXT, rows)


def test_needs_delivered_reset_alias():
    with pytest.raises(R.PortRelayError, match="delivered-reset alias"):
        R.apply(TXT.replace("wire rst_n = arst_n;", "wire rst_n = rst_n_t0;"), [dict(name="h", depth=1, sinks=["u_bin_a"])])


def test_sink_on_other_reset_rejected():
    t = TXT.replace("u_bin_a (.clk(clk), .rst_n(rst_n)", "u_bin_a (.clk(clk), .rst_n(other)")
    with pytest.raises(R.PortRelayError, match="not the delivered rst_n"):
        R.apply(t, [dict(name="h", depth=1, sinks=["u_bin_a"])])


IST_TXT = TXT.replace("    ot_dp_st #(.W(1)) u_bout_b",
                      "    ot_dp_st #(.W(1)) u_ist_a_0 (.clk(clk), .rst_n(rst_n), .d(a_q), .ea(a_eq), .q(), .eq());\n    ot_dp_st #(.W(1)) u_bout_b")


def test_relay_on_native_station_flop_binds():
    # a u_ist_* station (kit_istations / native_istations output) is an ot_dp_st on rst_n: a relay row may name it
    out, rec = R.apply(IST_TXT, [dict(name="s", depth=2, sinks=["u_ist_a_0"])])
    assert "u_ist_a_0 (.clk(clk), .rst_n(prl_s_1)," in out
    assert rec[0]["sinks"] == ["u_ist_a_0"]


def test_relay_on_station_fails_before_materialization():
    with pytest.raises(R.PortRelayError, match="not an emitted ot_dp_st"):
        R.apply(TXT, [dict(name="s", depth=2, sinks=["u_ist_a_0"])])


def test_bind_applies_port_relays_after_station_materialization():
    import pathlib
    src = (pathlib.Path(__file__).with_name("bind.py")).read_text()
    assert src.index("native_istations.materialize(self, tn, f)") < src.index("reset_port_relays.apply(f.read_text(), port_relays)")
