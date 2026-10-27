"""CLOCK-KV-R20 (NUMBER-CHECK-KV-R19): split stubs must state their real hops in mesh.json taps."""
import die_clock_mesh as DM


def test_annotate_split_tap_reports_longest_hop():
    rows = [dict(port="t_a__clk", stub_um=510.76), dict(port="t_b__clk", stub_um=40.0)]
    DM.annotate_stub_splits(rows, {"t_a__clk": dict(driver="ckm_s_1", reps=["ckm_x_0"], hops_um=[255.1, 256.18])})
    a, b = rows
    assert a["stub_um"] == 256.18 and a["stub_total_um"] == 510.76
    assert a["stub_hops_um"] == [255.1, 256.18] and a["stub_reps"] == ["ckm_x_0"]
    assert b == dict(port="t_b__clk", stub_um=40.0)


def test_annotate_no_splits_is_identity():
    rows = [dict(port="t_a__clk", stub_um=12.0)]
    DM.annotate_stub_splits(rows, None)
    assert rows == [dict(port="t_a__clk", stub_um=12.0)]
