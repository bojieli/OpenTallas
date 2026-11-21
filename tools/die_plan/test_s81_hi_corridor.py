"""S81-HI-CORRIDOR: shared hi-quad bank sites (check / sites / seed) on a synthetic leaf type."""
import copy
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s81_hi_corridor as H  # noqa: E402

L = 114.48


def plan():
    cores = [dict(inst="u_lf.u_vn.u_a", module="ot_s81sl_vn_a", origin_um=[500.0, 300.0], orient="R0", outline_um=[356.4, 164.16])]
    for k in range(16):
        col, row = k % 2, k // 2
        cores.append(dict(inst=f"u_lf.u_vp.g_ln[{k}].u_l", module="ot_dsrom_su_hcpost_lane_pr",
                          origin_um=[200.0 + col * (L + 11.0), 20.0 + row * (L + 15.0)], orient="MX", outline_um=[L, L]))
    st = []
    for k in range(16):
        x0, y0 = cores[1 + k]["origin_um"]
        # stage 0 at the vn face, stage 1 alternately west gap / vn face (centroid lands inside a lane), stage 2 at the lane
        s1 = [x0 + L + 5.5, y0 + 40] if k % 2 == 0 else [490.0, y0 + 40]
        st.append(dict(bits=523, launch="core:u_lf.u_vn.u_a.hw_d", capture=f"u_lf.u_vp.g_ln[{k}].u_l",
                       conn="x", from_um=[500.0, 380.0], regs_um=[[490.0, 380.0], s1, [x0 + L + 2, y0 + 60]],
                       to_um=[x0 + L, y0 + 60], note=""))
    t = dict(outline_um=[1000.0, 1200.0], hard_cores=cores, internal_stations=st)
    return {"partition_types": {"ot_s81sl_leaf__t99": t}}


def test_check_flags_bank_inside_lane():
    r = H.check(plan(), r"t99", 2)["ot_s81sl_leaf__t99"]
    assert r["banks_inside_core"] >= 1 and r["verdict"] == "OVER"


def test_sites_moves_every_shared_bank_out_of_cores_and_keeps_counts():
    P = plan()
    before = copy.deepcopy(P)
    rows = H.sites(P, r"t99", 2, 4.32)
    assert rows and all(r["result"] == "sited" for r in rows)
    t, t0 = P["partition_types"]["ot_s81sl_leaf__t99"], before["partition_types"]["ot_s81sl_leaf__t99"]
    assert [len(e["regs_um"]) for e in t["internal_stations"]] == [len(e["regs_um"]) for e in t0["internal_stations"]]
    assert [e["regs_um"][2] for e in t["internal_stations"]] == [e["regs_um"][2] for e in t0["internal_stations"]]
    r = H.check(P, r"t99", 2)["ot_s81sl_leaf__t99"]
    assert r["banks_inside_core"] == 0
    for g in range(4):     # one site per quad stage
        es = [e for e in t["internal_stations"] if int(e["capture"].split("[")[1].split("]")[0]) // 4 == g]
        for j in range(2):
            assert len({tuple(e["regs_um"][j]) for e in es}) == 1


def test_seed_B_puts_quads_in_columns():
    sd, rep = H.seed(plan(), r"t99", "B", 30.24)
    assert rep["ot_s81sl_leaf__t99"]["quads_in_one_column"] == 4
    pos = sd["ot_s81sl_leaf__t99"]
    assert sorted(tuple(v["origin_um"]) for v in pos.values()) == sorted(
        tuple(c["origin_um"]) for c in plan()["partition_types"]["ot_s81sl_leaf__t99"]["hard_cores"][1:])


def test_cli_check(tmp_path):
    p = tmp_path / "p.json"; p.write_text(json.dumps(plan()))
    out = subprocess.run([sys.executable, "-I", str(HERE / "s81_hi_corridor.py"), "check", str(p), "--types", "t99"],
                         capture_output=True, text=True, check=True).stdout
    assert "HI_CORRIDOR_CHECK" in out and "OVER" in out


def test_apply_moves_lane_with_riding_coordinates_only():
    P = plan()
    t = P["partition_types"]["ot_s81sl_leaf__t99"]
    t["clock"] = {"landing_contract": [{"inst": "u_lf.u_vp.g_ln[3].u_l", "pin_um": [1.0, 2.0], "xy": [1.0, 6.0]}],
                  "taps": [{"name": "u_lf.u_vp.g_ln[3].u_l.clk", "kind": "core", "xy": [5.0, 5.0, 1]}]}
    e3 = [e for e in t["internal_stations"] if e["capture"] == "u_lf.u_vp.g_ln[3].u_l"][0]
    e4 = copy.deepcopy([e for e in t["internal_stations"] if e["capture"] == "u_lf.u_vp.g_ln[4].u_l"][0])
    shared, last, to = copy.deepcopy(e3["regs_um"][:2]), list(e3["regs_um"][2]), list(e3["to_um"])
    o = t["hard_cores"][4]["origin_um"]
    n = H.move_lanes(t, {"u_lf.u_vp.g_ln[3].u_l": {"origin_um": [o[0] + 4.32, o[1] + 8.64], "orient": "MX"}}, 2)
    assert n["lanes"] == 1 and n["clock"] == 3
    r4 = lambda v: [round(x, 4) for x in v]  # noqa: E731
    assert e3["to_um"] == r4([to[0] + 4.32, to[1] + 8.64]) and e3["regs_um"][2] == r4([last[0] + 4.32, last[1] + 8.64])
    assert e3["regs_um"][:2] == shared
    assert [e for e in t["internal_stations"] if e["capture"] == "u_lf.u_vp.g_ln[4].u_l"][0]["regs_um"] == e4["regs_um"]
    assert t["clock"]["taps"][0]["xy"] == [9.32, 13.64, 1]


def test_seed_A_gaps_at_least_corridor_and_no_overlap():
    sd, rep = H.seed(plan(), r"t99", "A", 30.24)
    pos = [v["origin_um"] for v in sd["ot_s81sl_leaf__t99"].values()]
    for i, a in enumerate(pos):
        for b in pos[i + 1:]:
            gx = max(b[0] - (a[0] + L), a[0] - (b[0] + L)); gy = max(b[1] - (a[1] + L), a[1] - (b[1] + L))
            assert max(gx, gy) >= 30.24 - 1e-6


def test_apply_clears_added_tap_left_under_moved_lane():
    P = plan()
    t = P["partition_types"]["ot_s81sl_leaf__t99"]
    o = t["hard_cores"][4]["origin_um"]
    new = [o[0] + 30.24, o[1]]
    t["clock"] = {"added_taps": [{"name": "clk_t0", "xy": [new[0] + 50.0, new[1] + 50.0]},
                                 {"name": "clk_t1", "xy": [900.0, 1100.0]}]}
    n = H.move_lanes(t, {"u_lf.u_vp.g_ln[3].u_l": {"origin_um": new, "orient": "MX"}}, 2)
    assert [m[0] for m in n["taps_moved"]] == ["clk_t0"]
    x, y = t["clock"]["added_taps"][0]["xy"]
    assert not (new[0] - 8.65 < x < new[0] + L + 8.65 and new[1] - 8.65 < y < new[1] + L + 8.65)
    assert t["clock"]["added_taps"][1]["xy"] == [900.0, 1100.0]


def test_apply_keeps_added_taps_legal_against_grid_taps_and_halos():
    """A3 bind failure 11-19 (leaf__t28 clk_t38 'violates outline/halo/tap spacing'): the old rule looked only at the
    moved lane boxes and the other added taps.  Now every added tap must pass the bind's rule after the move: outline
    margin, every placed box + tap clear, tap clear to every grid tap (the grid is re-derived on the moved cores)."""
    P = plan()
    t = P["partition_types"]["ot_s81sl_leaf__t99"]
    _, _, grid0 = H._tap_rule(t)
    gx, gy = grid0[4]                                             # an interior grid tap
    o = t["hard_cores"][4]["origin_um"]
    new = [o[0] + 30.24, o[1]]
    t["clock"] = {"tap_mode": "grid+explicit", "added_taps": [
        {"name": f"clk_t{len(grid0)}", "xy": [o[0] + L + 20.0, o[1] + 50.0]},        # free now, under the moved lane after
        {"name": f"clk_t{len(grid0) + 1}", "xy": [gx + 2.16, gy + 2.16]},            # on a grid tap, no lane near it
        {"name": f"clk_t{len(grid0) + 2}", "xy": [900.0, 1100.0]}]}                  # legal: must not move
    assert H.added_tap_errors(t) == [f"clk_t{len(grid0) + 1}"]                       # before the move only the grid one
    n = H.move_lanes(t, {"u_lf.u_vp.g_ln[3].u_l": {"origin_um": new, "orient": "MX"}}, 2)
    assert {m[0] for m in n["taps_moved"]} == {f"clk_t{len(grid0)}", f"clk_t{len(grid0) + 1}"}
    assert H.added_tap_errors(t) == []
    assert t["clock"]["added_taps"][2]["xy"] == [900.0, 1100.0]
    clear, B, grid = H._tap_rule(t)
    for a in t["clock"]["added_taps"]:
        x, y = a["xy"]
        assert all(abs(x - p) >= clear or abs(y - q) >= clear for p, q in grid)
        assert not any(x0 < x < x1 and y0 < y < y1 for x0, y0, x1, y1 in B)


def test_cli_apply_runs_isolated(tmp_path):
    """python3 -I (the lane rule) leaves the script directory off sys.path: the tap rule must still import schema"""
    P = plan()
    t = P["partition_types"]["ot_s81sl_leaf__t99"]
    o = t["hard_cores"][4]["origin_um"]
    t["clock"] = {"tap_mode": "grid+explicit", "added_taps": [{"name": "clk_t9", "xy": [o[0] + L + 20.0, o[1] + 50.0]}]}
    (tmp_path / "p.json").write_text(json.dumps(P))
    (tmp_path / "seed.json").write_text(json.dumps({"ot_s81sl_leaf__t99": {
        "u_lf.u_vp.g_ln[3].u_l": {"origin_um": [o[0] + 30.24, o[1]], "orient": "MX"}}}))
    r = subprocess.run([sys.executable, "-I", str(HERE / "s81_hi_corridor.py"), "apply", str(tmp_path / "p.json"),
                        "--seed", str(tmp_path / "seed.json"), "--out", str(tmp_path / "o.json")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-600:]
    assert "clk_t9" in r.stdout


def test_types_without_hard_cores_are_skipped_with_warning(capsys):
    P = plan()
    P["partition_types"]["ot_s81sl_kv_leaf__t2"] = dict(outline_um=[100.0, 100.0], hard=True, internal_stations=[])
    rex = r"^ot_s81sl_(kv_)?leaf__t\d+$"
    rep = H.check(copy.deepcopy(P), rex, 2)
    assert "ot_s81sl_kv_leaf__t2" not in rep and "ot_s81sl_leaf__t99" in rep
    Q = copy.deepcopy(P)
    rows = H.sites(Q, rex, 2, 8.64)
    assert rows and all(r["type"] == "ot_s81sl_leaf__t99" for r in rows)
    assert Q["partition_types"]["ot_s81sl_kv_leaf__t2"] == P["partition_types"]["ot_s81sl_kv_leaf__t2"]
    assert "HI_CORRIDOR_WARN ot_s81sl_kv_leaf__t2" in capsys.readouterr().err


def _far_plan():
    """vn face 300 um further east: the far quads are more than two hops from the first bank"""
    P = plan()
    t = P["partition_types"]["ot_s81sl_leaf__t99"]
    t["outline_um"] = [1400.0, 1200.0]
    for h in t["hard_cores"]:
        if h["inst"] == "u_lf.u_vn.u_a":
            h["origin_um"] = [800.0, 300.0]
    for e in t["internal_stations"]:
        e["from_um"] = [800.0, 380.0]; e["regs_um"][0] = [790.0, 380.0]
        x, y = e["to_um"]
        e["regs_um"][1] = [(790.0 + x) / 2, (380.0 + y) / 2]
    return P


def test_add_stage_gives_every_hi_row_one_more_stage_and_closes_the_hops():
    P = _far_plan()
    t = P["partition_types"]["ot_s81sl_leaf__t99"]
    base = copy.deepcopy(P)
    r0 = H.sites(copy.deepcopy(base), "t99", 2, 8.64)
    assert any(x["result"] != "sited" for x in r0)                     # plain form C refuses rows here
    r = H.sites(P, "t99", 2, 8.64, add_stage=True)
    assert all(x["result"] == "sited" for x in r), [x for x in r if x["result"] != "sited"][:3]
    assert r[-1]["add_stage"] == 1 and r[-1]["hi_depth"] == 4 and r[-1]["hi_rows"] == 16
    B = H.boxes(t)
    for e in t["internal_stations"]:
        assert len(e["regs_um"]) == 4                                   # uniform depth: one CS_HI_D per leaf
        assert max(H._hops(e)) <= 400.0 + 1e-6
        assert all(H.clear(p, B) >= 8.64 for p in e["regs_um"][:3])     # shared banks and the new stage in free channels
        assert "S81-HI-STAGE +1" in e["note"]
    for g in range(4):                                                  # the two shared stages stay shared per quad
        es = [e for e in t["internal_stations"] if int(H.LN.search(e["capture"])[1]) // 4 == g]
        assert len({tuple(e["regs_um"][0]) for e in es}) == 1 and len({tuple(e["regs_um"][1]) for e in es}) == 1


def test_add_stage_leaves_a_type_alone_when_plain_siting_works():
    P = plan(); Q = plan()
    assert H.sites(P, "t99", 2, 8.64, add_stage=True) == H.sites(Q, "t99", 2, 8.64)
    assert P == Q


def test_refused_quad_keeps_its_old_rows_and_no_row_gets_longer():
    """FABLE-PD-S81-0015 11-20: 'REFUSED final hop' still wrote the moved site (plan_j4a: 491 rows over 405 um)"""
    P = _far_plan()
    base = copy.deepcopy(P)
    r = H.sites(P, "t99", 2, 8.64)
    t, t0 = P["partition_types"]["ot_s81sl_leaf__t99"], base["partition_types"]["ot_s81sl_leaf__t99"]
    refused = {x["quad"] for x in r if x["result"] != "sited"}
    assert refused and all("quad" in x for x in r)
    for e, e0 in zip(t["internal_stations"], t0["internal_stations"]):
        g = int(H.LN.search(e["capture"])[1]) // 4
        if g in refused:
            assert e == e0                                               # regs and note untouched
        assert max(H._hops(e)) <= max(400.0, max(H._hops(e0))) + 1e-6    # no row of the type is longer than before
    sited = {x["quad"] for x in r if x["result"] == "sited"}
    assert not (sited & refused)                                         # a quad is sited whole or not at all


# ---- BANK FOOTPRINT (FABLE-FIX-S81-LEAF-R4 11-21): a site is a bank of flops, not a point ----
def test_bank_rad_matches_the_measured_bank_sizes():
    assert H.bank_rad(1) == 0 and H.bank_rad(257) == 11 and H.bank_rad(1025) == 23
    # 1,025 flops: about 100 x 12 um on the 2.16 x 0.27 um station grid (measured in t44 3_place.odb: about 95 x 12)
    assert 95 < 2 * H.bank_rad(1025) * H.CP < 105 and 11 < 2 * H.bank_rad(1025) * H.RH < 13.5


def test_seat_bank_free_field_is_clean():
    f = H.seat_bank((500.0, 500.0), 1025, [], [1000.0, 1000.0])
    assert f["ok"] and f["R"] == f["R0"] == 23 and f["split"] == []


def test_seat_bank_in_a_narrow_gap_between_two_cores_is_a_pile_up():
    B = [("a", 0.0, 0.0, 100.0, 114.0), ("b", 110.8, 0.0, 210.8, 114.0)]
    f = H.seat_bank((105.4, 57.0), 1025, B, [400.0, 400.0])
    assert f["fit"] and f["pile"] and f["spill"] > H.FP_SPILL
    assert H.clear((105.4, 57.0), B) > 4.32          # the POINT test alone passes this site at min-clear 4.32


def test_seat_bank_astride_a_core_is_split():
    B = [("ln", 100.0, 0.0, 120.0, 50.0)]
    f = H.seat_bank((110.0, 51.6), 1025, B, [400.0, 400.0])
    assert f["split"] == ["ln"] and not f["ok"]
    assert (lambda g: g["ok"] and not g["pile"])(H.seat_bank((110.0, 80.0), 1025, B, [400.0, 400.0]))     # clear of the core by more than the bank height


def test_seat_bank_goes_round_an_earlier_bank_and_the_outline():
    a = H.seat_bank((200.0, 200.0), 1025, [], [400.0, 400.0])
    b = H.seat_bank((200.0, 200.0), 1025, [], [400.0, 400.0], occ=[a["bbox_um"]])
    assert b["R"] > a["R"]
    edge = H.seat_bank((1.0, 1.0), 1025, [], [400.0, 400.0])
    assert edge["fit"] and edge["bbox_um"][0] >= 0 and edge["bbox_um"][1] >= 0 and edge["R"] > a["R"]


def test_check_counts_bad_per_lane_banks_at_gs0():
    """GS 0 has no shared bank; the per-lane banks (3 stages a lane, stage 2 beside the lane in the 11-um column gap) are
    seated and counted: split banks make the type OVER, pile-ups are reported"""
    r = H.check(plan(), r"t99", 0)["ot_s81sl_leaf__t99"]
    assert r["banks"] == 0 and r["lane_banks_fp_bad"] and all(b["flops"] == 524 for b in r["lane_banks_fp_bad"])
    assert r["banks_fp_bad"] + r["banks_pile_up"] >= 8
    assert (r["verdict"] == "OVER") == (r["banks_fp_bad"] > 0)


def test_sites_rows_carry_the_footprint_and_shared_banks_are_clean():
    P = plan()
    rows = H.sites(P, r"t99", 2, 4.32)
    assert all(r["fp_ok"] and not r["fp_pile"] and r["fp_split"] == [] and r["flops"] == 4 * 524 for r in rows)
    r = H.check(P, r"t99", 2)["ot_s81sl_leaf__t99"]
    assert all(b["fp_ok"] for b in r["bank_sites"])


def test_banks_on_one_spot_stack_through_the_grid():
    g = {}
    a = H.seat_bank((200.0, 200.0), 1025, [], [400.0, 400.0], grid=g)
    b = H.seat_bank((200.0, 200.0), 1025, [], [400.0, 400.0], grid=g)
    c = H.seat_bank((200.0, 200.0), 1025, [], [400.0, 400.0], grid=g)
    assert a["R"] == 23 and b["R"] > 30 and c["R"] > b["R"] and a["ok"]
    assert sum(hi - lo + 1 for iv in g.values() for lo, hi in iv) >= 3 * 1025


def test_one_bank_against_a_core_face_or_in_a_28um_channel_is_not_a_pile_up():
    face = H.seat_bank((100.0, 208.64), 1025, [("a", 0.0, 0.0, 200.0, 200.0)], [400.0, 400.0])
    assert face["ok"] and not face["pile"] and face["spill"] <= 1.6
    chan = H.seat_bank((114.0, 200.0), 1025, [("a", 0.0, 0.0, 100.0, 400.0), ("b", 128.08, 0.0, 228.0, 400.0)], [400.0, 400.0])
    assert chan["ok"] and not chan["pile"] and 1.5 < chan["spill"] < H.FP_SPILL


def _two_vn_plan():
    """one lane fed from two faces N and S of ANOTHER lane core: the bits-weighted centroid of its stage lands in that core"""
    cores = [dict(inst="u_lf.u_vn.u_a", module="vn", origin_um=[300.0, 260.0], orient="R0", outline_um=[100.0, 100.0]),
             dict(inst="u_lf.u_vn.u_b", module="vn", origin_um=[300.0, 40.0], orient="R0", outline_um=[100.0, 100.0]),
             dict(inst="u_lf.u_vp.g_ln[0].u_l", module="ln", origin_um=[20.0, 143.0], orient="R0", outline_um=[L, L]),
             dict(inst="u_lf.u_vp.g_ln[1].u_l", module="ln", origin_um=[160.0, 143.0], orient="R0", outline_um=[L, L])]
    st = [dict(bits=523, launch="core:u_lf.u_vn.u_a.hw_d", capture="u_lf.u_vp.g_ln[0].u_l", conn="x", from_um=[300.0, 300.0],
               regs_um=[[220.0, 290.0]], to_um=[20.0 + L, 250.0], note=""),
          dict(bits=523, launch="core:u_lf.u_vn.u_b.hw_d", capture="u_lf.u_vp.g_ln[0].u_l", conn="x", from_um=[300.0, 100.0],
               regs_um=[[220.0, 110.0]], to_um=[20.0 + L, 150.0], note=""),
          dict(bits=300, launch="core:u_lf.u_vp.g_ln[1].u_l.ho_d", capture="u_lf.u_vn.u_a", conn="x", from_um=[160.0 + L, 200.0],
               regs_um=[[285.0, 200.0]], to_um=[300.0, 300.0], note="")]
    return {"partition_types": {"ot_s81sl_leaf__t98": dict(outline_um=[500.0, 400.0], hard_cores=cores, internal_stations=st)}}


def test_lane_bank_centroid_in_another_lane_is_found_and_lane_sites_fixes_it():
    P = _two_vn_plan()
    r = H.check(P, r"t98", 0)["ot_s81sl_leaf__t98"]
    assert r["banks_fp_bad"] >= 1 and r["verdict"] == "OVER"
    assert any(b["site"] == [220.0, 200.0] and b["flops"] == 524 and b["fp_split"] for b in r["lane_banks_fp_bad"])
    before = copy.deepcopy(P)
    rows = H.lane_sites(P, r"t98", 0, 8.64)
    assert rows and all(x["result"] == "sited" and x["fp_ok"] and not x["fp_pile"] for x in rows)
    assert {(x["cls"], x["flops"]) for x in rows} == {("hi", 524), ("ho", 301)}
    t, t0 = P["partition_types"]["ot_s81sl_leaf__t98"], before["partition_types"]["ot_s81sl_leaf__t98"]
    hi = [e for e in t["internal_stations"] if e["capture"].endswith("g_ln[0].u_l")]
    assert hi[0]["regs_um"] == hi[1]["regs_um"]                       # one site for the whole lane stage
    assert H.clear(hi[0]["regs_um"][0], H.boxes(t)) >= 8.64
    assert all(max(H._hops(e)) <= H.LANE_LIM for e in t["internal_stations"])
    assert [(e["bits"], len(e["regs_um"]), e["from_um"], e["to_um"]) for e in t["internal_stations"]] == \
           [(e["bits"], len(e["regs_um"]), e["from_um"], e["to_um"]) for e in t0["internal_stations"]]
    r = H.check(P, r"t98", 0)["ot_s81sl_leaf__t98"]
    assert r["banks_fp_bad"] == 0 and r["banks_pile_up"] == 0 and r["verdict"] == "OK"


def _far_two_vn_plan():
    """S81-LANE-BANK-ALL: one lane fed from two vn cores 600 um apart (t11 ln_0 form): no single site is within 295 um of both"""
    cores = [dict(inst="u_lf.u_vn.u_a", module="vn", origin_um=[500.0, 700.0], orient="R0", outline_um=[100.0, 100.0]),
             dict(inst="u_lf.u_vn.u_b", module="vn", origin_um=[500.0, 100.0], orient="R0", outline_um=[100.0, 100.0]),
             dict(inst="u_lf.u_vp.g_ln[0].u_l", module="ln", origin_um=[100.0, 393.0], orient="R0", outline_um=[L, L])]
    st = [dict(bits=256, launch="core:u_lf.u_vn.u_a.hw_d", capture="u_lf.u_vp.g_ln[0].u_l", conn="x", from_um=[500.0, 750.0],
               regs_um=[[450.0, 620.0], [300.0, 520.0]], to_um=[100.0 + L, 480.0], note=""),
          dict(bits=256, launch="core:u_lf.u_vn.u_b.hw_d", capture="u_lf.u_vp.g_ln[0].u_l", conn="x", from_um=[500.0, 150.0],
               regs_um=[[450.0, 280.0], [300.0, 380.0]], to_um=[100.0 + L, 420.0], note="")]
    return {"partition_types": {"ot_s81sl_leaf__t97": dict(outline_um=[700.0, 900.0], hard_cores=cores, internal_stations=st)}}


def test_lane_sites_uses_the_cbc_hop_so_a_lane_fed_from_two_far_vn_cores_is_sited():
    P = _far_two_vn_plan()
    rows = H.lane_sites(copy.deepcopy(P), r"t97", 0, 8.64, lim_um=295.0)       # the old planning hop: the lane kept its per-row sites
    assert any(x.get("kept_old") for x in rows)
    rows = H.lane_sites(P, r"t97", 0, 8.64)
    assert rows and all(x["result"] == "sited" for x in rows)
    es = P["partition_types"]["ot_s81sl_leaf__t97"]["internal_stations"]
    assert es[0]["regs_um"] == es[1]["regs_um"]                                # one site per lane stage, both rows
    assert all(max(H._hops(e)) <= H.LANE_LIM + 1e-6 for e in es)


def test_lane_sites_refused_lane_keeps_its_rows():
    P = _two_vn_plan()
    before = copy.deepcopy(P)
    rows = H.lane_sites(P, r"t98", 0, 8.64, lim_um=60.0)   # no point is within 60 um of both vn faces and the lane
    assert any(x["result"].startswith("REFUSED") and x.get("kept_old") for x in rows)
    t, t0 = P["partition_types"]["ot_s81sl_leaf__t98"], before["partition_types"]["ot_s81sl_leaf__t98"]
    for e, e0 in zip(t["internal_stations"], t0["internal_stations"]):
        if max(H._hops(e0)) > 60.0:
            assert max(H._hops(e)) <= max(H._hops(e0)) + 1e-6


def test_bank_flops_as_built_and_landing_bands_are_closed():
    es = [dict(bits=256, capture="a"), dict(bits=256, capture="a"), dict(bits=3, capture="a"), dict(bits=256, capture="b")]
    assert H.lane_flops(es[:3]) == 257 and H.quad_flops(es) == 514
    P = _two_vn_plan()
    t = P["partition_types"]["ot_s81sl_leaf__t98"]
    assert H.band_rects(t) == []
    rows0 = H.lane_sites(copy.deepcopy(P), r"t98", 0, 8.64)
    site0 = next(x["new"] for x in rows0 if x["cls"] == "hi")
    band = [site0[0] - 30.0, site0[1] - 10.0, site0[0] + 30.0, site0[1] + 10.0]
    t["clock"] = dict(band_fixed_um=dict(ft9_i=dict(rect_um=band)))
    assert H.band_rects(t) == [tuple(band)]
    rows = H.lane_sites(P, r"t98", 0, 8.64)
    q = next(x["new"] for x in rows if x["cls"] == "hi")
    assert not (band[0] - 8.64 < q[0] < band[2] + 8.64 and band[1] - 8.64 < q[1] < band[3] + 8.64)
    f = H.seat_bank(tuple(site0), 524, H.boxes(t), t["outline_um"], [tuple(band)])
    assert f["bbox_um"][1] >= band[3] or f["bbox_um"][3] <= band[1] or f["split"] == [] and f["R"] > f["R0"]
