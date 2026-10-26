import copy
import pytest
from clock_landings import Landings, LandingError, requirements


def vehicle():
    def pin(name, direction):
        return dict(name=name, dir=direction, width=1, face="E", window_um=[1, 2], layers=["M8"])
    p = dict(partitions=[dict(name="a", type="A", origin_um=[0, 0]),
                         dict(name="b", type="B", origin_um=[10, 0])],
             partition_types={"A": dict(module="a_mod", outline_um=[10, 10], buses=[pin("fclk_out_x", "out")]),
                              "B": dict(module="b_mod", outline_um=[10, 10], buses=[pin("y", "in"), pin("fclk_in_y", "in"),
                                  pin("landing_ready_y", "out"), pin("landing_fault_y", "out")])},
             ports=[dict(id="P", width=4, kind="data", src=dict(part="a", bus="x"), dst=dict(part="b", bus="y"))])
    t = dict(regions=[dict(tag="r0", box_um=[0, 0, 10, 10]), dict(tag="r1", box_um=[10, 0, 20, 10])],
             ports=[dict(port="P", width=4, src="a", dst="b", src_region="r0", dst_region="r1", lane="L")])
    return p, t


def test_real_receiver_and_forwarded_clock_are_emitted():
    p, t = vehicle(); c = Landings(p, t)
    a = "module a_mod (\n input wire clk,\n output wire [4:0] x\n);\n assign x = 0;\nendmodule\n"
    b = "module b_mod (\n input wire clk,\n input wire [4:0] y // whole bundle\n);\n wire rst_n, rst_n_t0, rr_parent, run;\n ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));\n wire [4:0] y_q;\n assign y_q = y;\nendmodule\n"
    aa = c.type_rtl("A", a); bb = c.type_rtl("B", b)
    assert "assign fclk_out_x = clk;" in aa
    assert "ot_dp_clk_landing #(.W(5)) u_cland_y" in bb
    assert ".d(y), .q(cland_y)" in bb
    assert "assign y_q = cland_y;" in bb
    assert "input wire [4:0] y," in bb
    assert ".rst_n(cland_reset_y)" in bb
    assert "ot_dp_rrelay u_cland_rst_y (.clk(clk), .d(rr_parent), .q(cland_reset_y))" in bb
    top = "module die_bound_top (rst_n, clk_core);\n input wire rst_n;\n input wire clk_core;\n    a_mod a (\n        .clk(clk_core)\n    );\n    b_mod b (\n        .clk(clk_core)\n    );\nendmodule\n"
    tt = c.top_rtl(top)
    assert ".fclk_in_y(clock_landing_fwd_a__x)" in tt
    assert ".fclk_out_x(clock_landing_fwd_a__x)" in tt
    assert ".clk(clk_region_r1)" in tt
    assert ".landing_fault_y(clock_landing_fault[0])" in tt
    assert c.manifest()["implemented"] is True
    assert c.manifest()["physical_qualified"] is False
    assert c.manifest()["lane_added_cycles"] == {"L": 3}


def test_missing_physical_pin_rejects_metadata_only_landing():
    p, t = vehicle(); p["partition_types"]["B"]["buses"].pop()
    with pytest.raises(LandingError, match="declare placed scalar out pin landing_fault_y"):
        Landings(p, t)


def test_repeated_type_with_different_masks_requires_explicit_split():
    p, t = vehicle(); p["partitions"].append(dict(name="b2", type="B", origin_um=[10, 0]))
    with pytest.raises(LandingError, match="TYPE_SPLIT"):
        Landings(p, t)
    r = requirements(p, t)
    assert r["type_count_after"] == 3
    assert len(r["split_types"]["B"]) == 2


def test_stale_width_or_region_cannot_emit():
    p, t = vehicle(); t["ports"][0]["width"] = 5
    with pytest.raises(LandingError, match="stale"):
        Landings(p, t)
    p, t = vehicle(); t["ports"][0]["dst_region"] = "r2"
    with pytest.raises(LandingError, match="region conflict"):
        Landings(p, t)


def test_inventory_does_not_claim_hardware_or_physical_pass():
    p, t = vehicle(); c = Landings(p, t)
    assert c.manifest()["implemented"] is False
    r = requirements(p, t)
    assert r["required_new_scalar_pins"] == 4
    assert r["added_live_data_storage_flops"] == 25
