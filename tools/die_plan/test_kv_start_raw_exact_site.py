"""kv_start_corridor_event raw: exact relay sites from <type>.reset_tree.json and a START base nudged off a keepout edge
(S81 col_h10_r0_p1 11-24: rst_rl_286..293 at (1533.6, 773.28) print as 773.3 in the .sv comment, inside the grown keepout,
so every raw corridor died with 'START endpoint inside keepout or outside outline')."""
import json

import kv_start_corridor_event as KS

SV = '''
    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 9 depth 1 @ (20.0, 100.0)
    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_n_t9));  // raw pad tap 9 depth 2 @ (20.0, 100.3)
'''


def test_exact_site_overlays_rounded_sv_comment(tmp_path):
    (tmp_path / "kvx.reset_tree.json").write_text(json.dumps({"tree": {"relays": [
        {"q": "rst_rl_0", "d": "rst_root_n", "depth": 1, "xy": [20.04, 100.0]},
        {"q": "rst_n_t9", "d": "rst_rl_0", "depth": 2, "xy": [20.0, 100.28]}]}}))
    t = KS._relay_table(SV, str(tmp_path), "kvx")
    assert t["rst_n_t9"]["xy"] == (20.0, 100.28) and t["rst_n_t9"]["d"] == "rst_rl_0" and t["rst_n_t9"]["depth"] == 2
    assert t["rst_rl_0"]["xy"] == (20.04, 100.0)


def test_tree_json_alone_gives_the_table(tmp_path):
    (tmp_path / "kvx.reset_tree.json").write_text(json.dumps({"tree": {"relays": [
        {"q": "rst_rl_0", "d": "rst_root_n", "depth": 1, "xy": [20.0, 100.0]}]}}))
    assert KS._relay_table("", str(tmp_path), "kvx") == {"rst_rl_0": dict(d="rst_root_n", depth=1, xy=(20.0, 100.0))}


def test_sv_only_still_works(tmp_path):
    t = KS._relay_table(SV, str(tmp_path), "kvx")
    assert t["rst_n_t9"]["xy"] == (20.0, 100.3)


def test_start_on_keepout_edge_is_kept_and_just_inside_is_nudged():
    obs = [[100.0, 100.0, 200.0, 200.0]]          # grown by CLEAR_UM: [95.68 .. 204.32]
    edge = 204.32
    assert KS._legal_start((150.0, edge), obs, 600.0, 600.0, 4.32) == (150.0, edge)
    q = KS._legal_start((150.0, edge - 0.02), obs, 600.0, 600.0, 4.32)
    assert q is not None and not (95.68 < q[0] < 204.32 and 95.68 < q[1] < 204.32)
    assert abs(q[0] - 150.0) + abs(q[1] - (edge - 0.02)) < 0.1


def test_consumer_within_one_hop_of_the_raw_relay_needs_no_branch(tmp_path):
    body = ("    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 9 depth 1 @ (300.0, 100.0)\n"
            "    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_n_t9));  // raw pad tap 9 depth 2 @ (300.0, 100.0)\n"
            "    assign cland_start_raw = rst_n_t9;\n")
    (tmp_path / "kvx_part.sv").write_text("module kvx_part (input wire clk);\n" + body + "endmodule\n")
    t = {"outline_um": [600.0, 600.0], "clock": {"landing_contract": {"pins": [
        {"name": "cland_tstart_in", "xy_um": [300.0, 300.0]},
        {"name": "cland_fstart_out_near", "xy_um": [300.0, 200.0]},
        {"name": "cland_fstart_out_far", "xy_um": [580.0, 300.0]}], "bands": {}}}}
    rep = KS.raw_type(None, "kvx", t, str(tmp_path), 4.32, 10.8)
    assert rep["consumers"]["fstart:near"]["copies"] == 0
    names = [b["consumers"] for b in t["clock"]["landing_raw_branches"]]
    assert ["fstart:near"] not in names and ["fstart:far"] in names


def test_part_named_tree_json_is_read(tmp_path):
    (tmp_path / "kvx_part.reset_tree.json").write_text(json.dumps({"tree": {"relays": [
        {"q": "rst_rl_0", "d": "rst_root_n", "depth": 1, "xy": [20.0, 100.0]}]}}))
    assert KS._relay_table("", str(tmp_path), "kvx") == {"rst_rl_0": dict(d="rst_root_n", depth=1, xy=(20.0, 100.0))}


def test_existing_raw_branch_net_maps_back_to_its_original_relay(tmp_path):
    body = ("    ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rst_root_n), .q(rst_rl_0));  // raw pad tap 9 depth 1 @ (300.0, 100.0)\n"
            "    ot_dp_rrelay u_rrl_1 (.clk(clk), .d(rst_rl_0), .q(rst_n_t9));  // raw pad tap 9 depth 2 @ (300.0, 100.0)\n"
            "    assign cland_start_raw = cland_raw_o_0;\n")
    (tmp_path / "kvx_part.sv").write_text("module kvx_part (input wire clk);\n" + body + "endmodule\n")
    t = {"outline_um": [600.0, 600.0], "clock": {"landing_raw_branches": [
        {"name": "o", "base": "rst_rl_0", "stages": [{"original": "rst_n_t9", "xy_um": [300.0, 200.0]}], "consumers": ["origin"]}],
        "landing_contract": {"pins": [
            {"name": "cland_tstart_in", "xy_um": [300.0, 300.0]},
            {"name": "cland_fstart_out_far", "xy_um": [580.0, 300.0]}], "bands": {}}}}
    rep = KS.raw_type(None, "kvx", t, str(tmp_path), 4.32, 10.8)
    assert rep["raw"] == "rst_n_t9"
