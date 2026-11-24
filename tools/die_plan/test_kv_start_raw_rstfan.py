"""KV-PV-RSTRELAY 11-23: kv_start_corridor_event raw maps a RING-RSTFAN-1 copy (cland_start_raw = cland_rfan_<bus>_<k>) back to
the original ring reset relay net, the node clock_landings emits (no RSTFAN with raw branches) and RawBranches resolves."""
import pytest

import kv_start_corridor_event as KS
from landing_raw_branches import RawBranches

BODY = """
    ot_dp_rrelay u_rst_in (.clk(clk), .d(arst_n), .q(rst_root_n));  // pin register
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 9 depth 1 @ (20.0, 580.0)
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_rl_1));  // raw pad tap 9 depth 2 @ (20.0, 580.0)
    ot_dp_rrelay u_rrl_2 (.clk(clk), .d(rst_rl_1), .q(rst_rl_2));  // raw pad tap 9 depth 3 @ (20.0, 580.0)
    ot_dp_rrelay u_rrl_3 (.clk(clk), .d(rst_rl_2), .q(rst_rl_3));  // raw pad tap 9 depth 4 @ (20.0, 580.0)
"""
LANDING = """
    wire cland_reset_ft1_i;
    ot_dp_rrelay u_cland_rst_ft1_i (.clk(clk), .d(rst_rl_3), .q(cland_reset_ft1_i));
    wire cland_rfan_ft1_i_1;
    (* keep = "true" *) ot_dp_rrelay u_cland_rfan_ft1_i_1 (.clk(clk), .d(rst_rl_3), .q(cland_rfan_ft1_i_1));  // RING-RSTFAN-1 same-cycle copy of u_cland_rst_ft1_i for its far loads
    assign cland_start_raw = cland_rfan_ft1_i_1;
"""


def test_rstfan_copy_maps_to_original_ring_reset():
    assert KS.rstfan_original(BODY + LANDING, "cland_rfan_ft1_i_1") == ("cland_reset_ft1_i", "u_cland_rfan_ft1_i_1")
    assert KS.rstfan_original(BODY + LANDING, "rst_rl_3") == ("rst_rl_3", None)


def test_rstfan_copy_without_its_original_fails_closed():
    broken = LANDING.replace(".d(rst_rl_3), .q(cland_reset_ft1_i)", ".d(rst_rl_2), .q(cland_reset_ft1_i)")
    with pytest.raises(SystemExit, match="original relay"):
        KS.rstfan_original(BODY + broken, "cland_rfan_ft1_i_1")


def _type():
    return {"outline_um": [600.0, 600.0], "clock": {"landing_contract": {
        "pins": [{"name": "cland_tstart_in", "xy_um": [300.0, 300.0]},
                 {"name": "cland_fstart_out_a", "xy_um": [580.0, 20.0]}], "bands": {}}}}


def test_raw_step_names_the_original_relay_and_the_branch_validates(tmp_path):
    (tmp_path / "kvx_part.sv").write_text("module kvx_part (input wire clk);\n" + BODY + LANDING + "endmodule\n")
    t = _type()
    rep = KS.raw_type(None, "kvx", t, str(tmp_path), 4.32, 10.8)
    assert rep["raw"] == "cland_reset_ft1_i" and rep["rstfan_copy_mapped"]["copy"] == "u_cland_rfan_ft1_i_1"
    branches = t["clock"]["landing_raw_branches"]
    fs = next(b for b in branches if b["consumers"] == ["fstart:a"])
    assert fs["stages"][-1]["original"] == "cland_reset_ft1_i"
    assert all(s["original"] != "cland_rfan_ft1_i_1" for b in branches for s in b["stages"])
    # emitted form with branches: no RSTFAN, cland_start_raw = the original ring reset; the ring relay is a baseline relay
    emitted_landing = LANDING.split("    wire cland_rfan")[0] + "    assign cland_start_raw = cland_reset_ft1_i;\n"
    g = RawBranches("kvx", branches, BODY, t["outline_um"])
    g.baseline_relay("    ot_dp_rrelay u_cland_rst_ft1_i (.clk(clk), .d(rst_rl_3), .q(cland_reset_ft1_i));")
    uses = "\n".join(f"    ot_dp_landing_relay u_x_{i} (.clk(clk), .rst_raw_n({g.raw_for(r, 'cland_start_raw')}), .d(s), .q(q{i}));"
                     for i, r in enumerate(["origin", "fstart:a"]))
    rep2 = g.validate(BODY + emitted_landing + "\n".join(g.rtl) + "\n" + uses)
    assert rep2["flops"] == sum(len(b["stages"]) for b in branches)


def test_original_bound_copy_name_is_refused_by_rawbranches():
    """the pre-fix form: a stage naming the RSTFAN copy cannot resolve in the original body + baseline (bind EMIT)"""
    from landing_raw_branches import RawBranchError
    g = RawBranches("kvx", [{"name": "fs_a", "base": "rst_rl_2", "stages": [{"original": "rst_rl_3", "xy_um": [300.0, 300.0]},
                     {"original": "cland_rfan_ft1_i_1", "xy_um": [500.0, 100.0]}], "consumers": ["fstart:a"]}], BODY, [600.0, 600.0])
    g.baseline_relay("    ot_dp_rrelay u_cland_rst_ft1_i (.clk(clk), .d(rst_rl_3), .q(cland_reset_ft1_i));")
    use = f"    ot_dp_landing_relay u_x (.clk(clk), .rst_raw_n({g.raw_for('fstart:a', 'cland_start_raw')}), .d(s), .q(q));"
    with pytest.raises(RawBranchError, match="exactly one same-clk plain relay"):
        g.validate(BODY + LANDING + "\n".join(g.rtl) + "\n" + use)
