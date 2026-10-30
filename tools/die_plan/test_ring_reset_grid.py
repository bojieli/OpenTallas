"""IQF: landing raw-reset indices must be those of the emitted physical reset grid."""
import copy

import clock_landings as CL
import reset_tree as RT
import schema as S
from test_clock_landings import vehicle


def physical_vehicle():
    p, t = vehicle()
    p["die"] = dict(name="ring_grid", outline_um=[2000, 2000], reach_um=405)
    p["lanes"] = []
    p["budgets"] = dict(tap_pitch_um=400)
    b = p["partition_types"]["B"]
    b["outline_um"] = [800, 800]
    b["clock"] = dict(tap_um=[400, 400], layer="M9")
    b["buses"][0].update(face="N", window_um=[1, 2])
    t["regions"][1]["box_um"] = [10, 0, 810, 800]
    return p, t


def test_generated_clock_grid_is_the_reset_index_space():
    p, _ = physical_vehicle()
    expected = [(x, y) for _, x, y in RT._taps(S.Plan(p), "B")]
    assert len(expected) == 4
    assert CL.ring_taps(p, "B") == expected


def test_north_landing_uses_north_raw_reset_with_the_same_parent_depth():
    p, t = physical_vehicle()
    body = "module b_mod (\n input wire clk,\n input wire [4:0] y\n);\n"
    for i in range(4):
        body += (f"wire rst_n_t{i}, p{i};\n"
                 f"ot_dp_rrelay u_rrl_{i} (.clk(clk), .d(p{i}), .q(rst_n_t{i}));\n")
    body += "wire [4:0] y_q; assign y_q = y;\nendmodule\n"
    c = CL.Landings(p, t)
    out = c.type_rtl("B", body)
    assert ".rst_n(rst_n_t2)" in out
    reset = c.reset_placements["B"]["y"]
    assert reset["net"] == "rst_n_t2" and reset["copied_raw_parent"] == "p2"
    assert reset["extra_control_flops"] == 0


def test_explicit_noncore_taps_and_unconfigured_types_are_unchanged():
    p, _ = physical_vehicle()
    p["partition_types"]["B"]["clock"]["taps"] = [dict(xy=[71, 82]), dict(xy=[91, 102])]
    assert CL.ring_taps(p, "B") == [(71, 82), (91, 102)]
    bare = copy.deepcopy(p)
    bare["partition_types"]["B"].pop("clock")
    assert CL.ring_taps(bare, "B") == []
