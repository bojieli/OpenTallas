"""pytest: adv_leg405_chain (C-LEG405 tail copies / relay-poly chains / reset relay chains, R3-RSTREACH2 11-27)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_leg405_chain as A  # noqa: E402

# S81 c085 col_h10_r2__t1 shape: polyline through three corners, one relay_depth row for u_e15.xb_data (D = 1, nothing staged)
POLY_OK = {"group_re": "u_y_xd_u_e15_xb_data_0_0$", "max_hop_um": 405, "polyline_um": [[803.52, 937.44], [675.0, 937.44], [675.0, 1188.0], [577.0, 1188.0]]}
# KV pv shape (FABLE-RC-KV 11-27): a 1,388 um path with one station = two 694 um hops
POLY_LONG = {"group_re": "u_ts3_g$", "polyline_um": [[0.0, 0.0], [1000.0, 0.0], [1000.0, 388.0]]}


def raw(t, extra=None):
    r = {"partition_types": {"T": t}}
    r.update(extra or {})
    return r


def test_poly_length_is_manhattan_through_the_waypoints():
    assert A.poly_length(POLY_OK["polyline_um"]) == 477.1
    assert A.poly_length(POLY_LONG["polyline_um"]) == 1388.0


def test_poly_hop_is_path_over_stations_plus_one_and_flags_the_kv_pv_shape():
    t = {"relay_polylines": [POLY_OK, POLY_LONG], "relay_depth": [{"inst": "u_e15", "port": "xb_data", "D": 1, "stages_existing": 0, "path_um": 524.0},
                                                                  {"inst": "u_ts3", "port": "g", "D": 1, "stages_existing": 0}]}
    rows = {r[0]: r for r in A.poly_rows(t)}
    assert rows["u_y_xd_u_e15_xb_data_0_0$"][2:4] == (1, 238.6)        # 477.1 / 2 hops: fine
    ok = A.findings_by_check["LEG405-POLY"](raw(t), None)
    assert ok[0].startswith("WARN ADV-LEG405-POLY T ") and "694" in ok[0] and "needs 3 stations" in ok[0]
    assert "summary 1 of 1" in ok[-1] and "u_y_xd" not in ok[0]


def test_poly_with_no_relay_depth_row_is_unknown_not_clean():
    t = {"relay_polylines": [POLY_LONG]}
    ls = A.findings_by_check["LEG405-POLY"](raw(t), None)
    assert any("UNKNOWN-STATIONS" in x and "needs >= 3 stations" in x for x in ls)
    assert "0 of 1 types with polylines over limit, 1 with unknown" in ls[-1]


def test_poly_entry_max_hop_overrides_the_405_default():
    e = dict(POLY_OK, max_hop_um=200)
    t = {"relay_polylines": [e], "relay_depth": [{"inst": "u_e15", "port": "xb_data", "D": 1}]}
    assert "ADV-LEG405-POLY T" in A.findings_by_check["LEG405-POLY"](raw(t), None)[0]


def test_rrl_flags_the_reset_relay_hop_over_405_on_a_solved_tree():
    tree = {"root": [0.0, 0.0], "relays": [{"q": "rst_rl_0", "d": "rst_root_n", "xy": [300.0, 0.0]},
                                           {"q": "rst_rl_1", "d": "rst_rl_0", "xy": [300.0, 480.0]},
                                           {"q": "rst_n_t0", "d": "rst_rl_1", "xy": [310.0, 480.0]}]}
    assert [e[2] for e in A.relay_edges(tree)] == [300.0, 480.0, 10.0]
    ls = A.findings_by_check["LEG405-RRL"](raw({"hard": False}), None, tree_of=lambda tn, t: tree)
    assert "1 of 3 reset relay hop(s) over 405" in ls[0] and "rst_rl_1<-rst_rl_0 480" in ls[0] and "summary 1 of 1" in ls[-1]
    clean = dict(tree, relays=tree["relays"][:1])
    assert "summary 0 of 1" in A.findings_by_check["LEG405-RRL"](raw({"hard": False}), None, tree_of=lambda tn, t: clean)[-1]


def test_rrl_reads_the_published_landing_tree_when_the_type_has_one():
    ct = {"relays": [{"q": "a", "d": "b", "xy": [0.0, 0.0]}, {"q": "b", "d": "rst_root_n", "xy": [0.0, 500.0]}], "root": [0.0, 1000.0]}
    t = {"clock": {"landing_contract": {"collector_tree": ct, "collector_children": [{"node": "a"}]}}}
    ls = A.findings_by_check["LEG405-RRL"](raw(t, {"reset": {"reach_cap_um": 405}}), None)
    assert "published tree" in ls[0] and "500" in ls[0] and "reset.reach_cap_um 405" in ls[0]


def test_rrl_budget_leaves_unsolved_types_unchecked_not_clean():
    calls = []
    ls = A.findings_by_check["LEG405-RRL"](raw({"hard": False}), None, tree_of=lambda tn, t: calls.append(tn), budget_s=-1.0)
    assert not calls and "1 not checked past the -1 s budget" in ls[-1] and "summary 0 of 0" in ls[-1]


def test_rrl_on_a_published_tree_ignores_relays_no_collector_references():
    # S81 c085 shape: the published tree lists every solved relay; only the chain behind a referenced node is instantiated
    ct = {"relays": [{"q": "rst_n_t1", "d": "rst_rl_1", "xy": [0.0, 0.0]}, {"q": "rst_rl_1", "d": "rst_root_n", "xy": [0.0, 300.0]},
                     {"q": "rst_n_t9", "d": "rst_rl_9", "xy": [0.0, 0.0]}, {"q": "rst_rl_9", "d": "rst_root_n", "xy": [900.0, 0.0]}], "root": [0.0, 600.0]}
    t = {"clock": {"landing_contract": {"collector_tree": ct, "collector_children": [{"node": "rst_n_t1"}]}}}
    assert A.used_closure(t, ct) == {"rst_n_t1", "rst_rl_1"}
    ls = A.findings_by_check["LEG405-RRL"](raw(t), None)
    assert "summary 0 of 1" in ls[-1]
    t["clock"]["landing_contract"]["collector_children"].append({"node": "rst_n_t9"})
    ls = A.findings_by_check["LEG405-RRL"](raw(t), None)
    assert "summary 1 of 1" in ls[-1] and "rst_n_t9<-rst_rl_9 900" in ls[0]


def test_tail_copies_are_unchecked_without_bound_rtl_and_measured_with_it(tmp_path):
    ab = {"land_pad_tail_split": {"types": ["T.*"], "min_spread_um": 400, "hop_um": 380}}
    r = raw({"hard": False})
    ls = A.findings_by_check["LEG405-TAIL"](r, None, asbuilt=ab)
    assert "UNCHECKED 1 of 1" in ls[0] and "summary 0 of 0" in ls[-1]
    (tmp_path / "T.sv").write_text("// bound")
    ls = A.findings_by_check["LEG405-TAIL"](r, None, asbuilt=ab, bound_dir=str(tmp_path), census=lambda p, tn, sv, cfg: {"max_hop_um": 611.2 - 30})
    assert ls[0].startswith("WARN ADV-LEG405-TAIL T planned worst pad / tail-copy hop 581.2") and "summary 1 of 1" in ls[-1]
    ls = A.findings_by_check["LEG405-TAIL"](r, None, asbuilt=ab, bound_dir=str(tmp_path), census=lambda p, tn, sv, cfg: {"max_hop_um": 300.0})
    assert "summary 0 of 1" in ls[-1]


def test_tail_option_absent_selects_nothing_and_never_raises():
    assert "summary 0 types select" in A.findings_by_check["LEG405-TAIL"](raw({}), None)[-1]
    assert A.findings_by_check["LEG405-POLY"]({"partition_types": None}, None)


def test_registered_in_plan_advisory():
    import plan_advisory as PA
    names = {c[0] for c in PA.CHECKS}
    assert {"LEG405-POLY", "LEG405-RRL", "LEG405-TAIL"} <= names
