import copy

import pytest

import reset_replicate as RRP


SOURCE = """
module selected(input clk, other, input [2:0] incoming);
wire root_q, local_q;
wire [1:0] reset_alias;
assign reset_alias = {local_q[0], local_q[0]};
ot_hdc_v41x_kreg #(.R(1), .W(1)) root (
    .clk(clk), .d(1'b1), .rst_n(incoming[1]), .q(root_q)
);
ot_hdc_v41x_kreg #(.W(1), .R(1)) local_region (
    .clk(clk), .d(1'b1), .rst_n(root_q[0]), .q(local_q)
);
hard_cell u_hard (
    .rst_n(reset_alias[1]), .d(incoming[0])
);
endmodule
"""

SPEC = {
    "form": "kreg_branch",
    "driver": "root",
    "expected_reset_input": "incoming[1]",
    "branches": [
        {"name": "trunk", "parent": "root"},
        {"name": "side", "parent": "trunk"},
    ],
    "local_drivers": [{"name": "local_region", "branch": "trunk"}],
    "replicas": [{"name": "copy_region", "old_driver": "local_region", "branch": "side",
                  "sinks": [{"inst": "u_hard", "module": "hard_cell"}]}],
}


def test_default_keeps_legacy_output_byte_exact():
    assert RRP.apply(SOURCE, []) == (SOURCE, [])


def test_kreg_branches_preserve_root_stage_clock_and_release():
    bound = copy.deepcopy(SPEC)
    text, rows = RRP.apply(SOURCE, [bound])
    assert bound == SPEC
    assert ".rst_n(incoming[1]), .q(root_q)" in text
    assert ".rst_n(trunk_q), .q(local_q)" in text
    assert "BUFx4f_ASAP7_75t_R trunk (.A(root_q[0]), .Y(trunk_q))" in text
    assert "BUFx4f_ASAP7_75t_R side (.A(trunk_q), .Y(side_q))" in text
    assert "copy_region (.clk(clk), .d(1'b1), .rst_n(side_q), .q(copy_region_q))" in text
    assert ".rst_n(copy_region_q), .d(incoming[0])" in text
    assert rows == [{"form": "kreg_branch", "driver": "root", "copies": 1,
                     "transparent_branches": 2, "consumers": 1, "unchanged_registered_cycles": True}]


@pytest.mark.parametrize(("old", "new", "error"), [
    ("incoming[1]", "incoming[2]", "declared parent event"),
    (".clk(clk), .d(1'b1), .rst_n(root_q", ".clk(other), .d(1'b1), .rst_n(root_q", "native reset and clock"),
    (".R(1), .W(1)", ".R(0), .W(1)", "asynchronous"),
    ("reset_alias[1]", "reset_alias[2]", "no longer consumes"),
    ("{local_q[0], local_q[0]}", "{other, local_q[0]}", "no longer consumes"),
    ("hard_cell u_hard", "wrong_cell u_hard", "changed hard reset sink"),
])
def test_kreg_branch_rejects_changed_native_port_and_age(old, new, error):
    assert old in SOURCE
    with pytest.raises(RRP.ReplicateError, match=error):
        RRP.apply(SOURCE.replace(old, new), [SPEC])


def test_kreg_branch_rejects_cycle_and_duplicate_consumer():
    for modified, error in (("branch", "missing or forward"), ("consumer", "ambiguous or changed")):
        spec = copy.deepcopy(SPEC)
        if modified == "branch":
            spec["branches"][0]["parent"] = "side"
        else:
            spec["replicas"][0]["sinks"] *= 2
        with pytest.raises(RRP.ReplicateError, match=error):
            RRP.apply(SOURCE, [spec])
