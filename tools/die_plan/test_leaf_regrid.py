"""S81-LEAF-REGRID: lane slots (columns beside the vn face, landing-band keep-outs, 2-D slots round the vn cores), the +1 lane
stage, the hop fix, apply and check on a synthetic leaf."""
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import leaf_regrid as R  # noqa: E402
import s81_hi_corridor as H  # noqa: E402

L = R.LW
TN = "ot_s81sl_leaf__t97"


def plan(band=None):
    cores = [dict(inst="u_lf.u_vn.u_a", module="ot_s81sl_vn_a", origin_um=[600.0, 500.0], orient="R0", outline_um=[356.4, 164.16])]
    st = []
    for k in range(16):                              # 4 x 4 block, 6 um gaps: the measured bad form
        x0, y0 = 100.0 + (k % 4) * (L + 6.0), 340.0 + (k // 4) * (L + 6.0)
        cores.append(dict(inst=f"u_lf.u_vp.g_ln[{k}].u_l", module="ot_dsrom_su_hcpost_lane_pr", origin_um=[x0, y0], orient="R0", outline_um=[L, L]))
        st.append(dict(bits=256, launch="core:u_lf.u_vn.u_a.hw_d", capture=f"u_lf.u_vp.g_ln[{k}].u_l",
                       conn=f"core:u_lf.u_vn.u_a.hw_d|core:u_lf.u_vp.g_ln[{k}].u_l", from_um=[600.0, 520.0 + 6 * k],
                       regs_um=[[590.0, 520.0 + 6 * k], [x0 + L + 3.0, y0 + 60.0]], to_um=[x0 + L, y0 + 60.0], note=""))
    t = dict(outline_um=[1000.0, 1300.0], hard_cores=cores, internal_stations=st)
    if band:
        t["clock"] = dict(band_fixed_um=dict(ft3_i=dict(rect_um=list(band))))
    return {"partition_types": {TN: t}}


def _hit(slot, band, gap):
    x, y = slot
    a, b, c, d = band
    return x < c + gap and a < x + L + gap and y < d + gap and b < y + L + gap


def test_slots_are_columns_beside_the_vn_face_with_the_gaps():
    S, err = R.find_slots(plan()["partition_types"][TN])
    assert err is None and S["side"] == -1 and len(S["slots"]) >= 16 and S["strip"] >= R.STRIP - 1e-6
    cols = sorted(S["cols"])
    assert all(b - a >= L + R.COL_GAP - 1e-6 for a, b in zip(cols, cols[1:]))
    for x in cols:
        ys = sorted(y for sx, y in S["slots"] if sx == x)
        assert all(b - a >= L + R.ROW_GAP - 1e-6 for a, b in zip(ys, ys[1:]))


def test_no_slot_on_or_beside_a_landing_band():
    """t44 kit A 11-21: two moved lanes stood on the ft3_i / up_s landing bands and global_place stopped (OT_CLAND BAND FAIL)"""
    S0, _ = R.find_slots(plan()["partition_types"][TN])
    x, y = S0["slots"][len(S0["slots"]) // 2]
    band = (x + 10.0, y + 20.0, x + 100.0, y + 60.0)                     # a band under one free-form slot
    assert any(_hit(s, band, 0.0) for s in S0["slots"])
    S1, _ = R.find_slots(plan(band)["partition_types"][TN])
    assert S1["slots"] and not any(_hit(s, band, R.BAND_GAP - 1e-6) for s in S1["slots"])


def test_apply_moves_the_lanes_off_the_band_and_check_gates_it():
    S0, _ = R.find_slots(plan()["partition_types"][TN])
    x, y = sorted(S0["slots"], key=lambda s: abs(s[0] + L / 2 - S0["face_x"]) + abs(s[1] + L / 2 - 560.0))[0]
    band = (x + 10.0, y + 20.0, x + 100.0, y + 60.0)                     # under the slot the free form would use first
    P = plan(band)
    t = P["partition_types"][TN]
    r = R.regrid_type(TN, t, P, R.COL_GAP, R.ROW_GAP, R.STRIP)
    assert r["result"] == "moved", r
    lanes = [b for b in H.boxes(t) if H.LN.search(b[0])]
    assert len(lanes) == 16 and not any(b[1] < band[2] + R.BAND_GAP - 1e-6 and band[0] - R.BAND_GAP + 1e-6 < b[3]
                                        and b[2] < band[3] + R.BAND_GAP - 1e-6 and band[1] - R.BAND_GAP + 1e-6 < b[4] for b in lanes)
    R.seat(t)                                                             # as apply does: registers 8.64 um off every core
    c = R.check_type(TN, t, 0)
    assert c["lanes_on_band"] == [] and c["lane_gaps_under"] == 0 and c["sites_in_core"] == 0
    bad = copy.deepcopy(t)                                                # a band drawn over a placed lane fails the check
    b0 = lanes[0]
    bad["clock"]["band_fixed_um"]["ft3_i"]["rect_um"] = [b0[1] + 5.0, b0[2] + 5.0, b0[3] - 5.0, b0[2] + 40.0]
    cb = R.check_type(TN, bad, 0)
    assert cb["lanes_on_band"] == [b0[0]] and not cb["pass"]


def test_refused_type_keeps_its_rows_through_the_cli(tmp_path):
    import json, subprocess
    P = plan()
    t = P["partition_types"][TN]
    t["outline_um"] = [1000.0, 480.0]                                     # 3 rows a column: 12 slots for 16 lanes
    src = tmp_path / "p.json"; out = tmp_path / "o.json"
    src.write_text(json.dumps(P))
    r = subprocess.run([sys.executable, "-I", str(HERE / "leaf_regrid.py"), "apply", str(src), "--types", "t97", "--no-2d", "--out", str(out),
                        "--report", str(tmp_path / "r.json")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    rep = json.loads((tmp_path / "r.json").read_text())
    assert rep and rep[0]["result"].startswith("REFUSED")
    assert json.loads(out.read_text())["partition_types"][TN] == json.loads(src.read_text())["partition_types"][TN]


def plan_2d():
    """a core west of the vn face closes most of the columns: 16 lanes fit only with slots north / south of vn"""
    P = plan()
    t = P["partition_types"][TN]
    t["hard_cores"].append(dict(inst="u_lf.u_vsw", module="ot_s81sl_vsw", origin_um=[20.0, 20.0], orient="R0", outline_um=[410.0, 980.0]))
    for k, h in enumerate(c for c in t["hard_cores"] if H.LN.search(c["inst"])):     # the lanes start outside that core
        h["origin_um"] = [440.0 + (k % 4) * (L + 6.0), 700.0 + (k // 4) * (L + 6.0)]
        e = t["internal_stations"][k]
        e["to_um"] = [h["origin_um"][0] + L, h["origin_um"][1] + 60.0]
        e["regs_um"] = [[590.0, 520.0 + 6 * k], [e["to_um"][0] + 3.0, e["to_um"][1]]]
    return P


def test_2d_slots_when_the_columns_do_not_fit():
    P = plan_2d()
    t = P["partition_types"][TN]
    S, _ = R.find_slots(t)
    assert len(S["slots"]) < 16
    assert R.regrid_type(TN, copy.deepcopy(t), P, R.COL_GAP, R.ROW_GAP, R.STRIP, two_d=False)["result"].startswith("REFUSED")
    keep = copy.deepcopy(t)
    r = R.regrid_type(TN, t, P, R.COL_GAP, R.ROW_GAP, R.STRIP)
    assert r["result"] == "moved" and r["form"] == "2d", r
    lanes = [b for b in H.boxes(t) if H.LN.search(b[0])]
    other = [b for b in H.boxes(t) if not H.LN.search(b[0])]
    assert len(lanes) == 16
    for i, a in enumerate(lanes):
        for b in lanes[i + 1:]:              # x gap >= COL_GAP or y gap >= ROW_GAP
            assert max(a[1] - b[3], b[1] - a[3]) >= R.COL_GAP - 1e-6 or max(a[2] - b[4], b[2] - a[4]) >= R.ROW_GAP - 1e-6
        for o in other:                      # OBS_GAP to every non-lane core
            assert max(a[1] - o[3], o[1] - a[3], a[2] - o[4], o[2] - a[4]) >= R.OBS_GAP - 1e-6
        # the strip in front of the face stays open, and no lane goes past the far end of vn
        assert not (a[1] < S["face_x"] and S["face_x"] - R.STRIP < a[3] and a[2] < S["face_y"][1] + R.ROW_GAP and S["face_y"][0] - R.ROW_GAP < a[4])
        assert a[3] <= 600.0 + 356.4 + 1e-6
    assert any(a[1] >= 600.0 - 1e-6 or a[3] > 600.0 for a in lanes)          # some lane stands north / south of vn
    R.seat(t)
    hf = R.fix_hops(t, keep["internal_stations"])
    c = R.check_type(TN, t, 0)
    assert c["pass"] and c["sites_in_core"] == 0 and c["worst_hop_um"] <= R.HOP, (c, hf)
    for e in t["internal_stations"]:         # the path sites stand SEAT off every core (round the vn corner, not over it)
        assert all(H.clear(p, H.boxes(t)) >= R.SEAT - 1e-6 for p in e["regs_um"])


def test_router_goes_round_a_core():
    t = dict(outline_um=[600.0, 600.0], hard_cores=[dict(inst="u_lf.u_vq", origin_um=[200.0, 100.0], orient="R0", outline_um=[100.0, 400.0])])
    pts = R.Router(t).path([190.0, 300.0], [310.0, 300.0])
    assert pts and R.plen(pts) > 400.0                                    # 120 um apart, the core between them
    B = H.boxes(t)
    assert all(H.clear(p, B) >= R.SEAT - 1e-6 for p in pts[1:-1])


def plan_far():
    """one-station rows to lanes two hops and more from the vn face (a core closes the near columns)"""
    P = plan()
    t = P["partition_types"][TN]
    t["outline_um"] = [1500.0, 1300.0]
    vn = t["hard_cores"][0]
    vn["origin_um"] = [1100.0, 500.0]
    t["hard_cores"].append(dict(inst="u_lf.u_vsw", module="ot_s81sl_vsw", origin_um=[760.0, 4.0], orient="R0", outline_um=[260.0, 1290.0]))
    for e in t["internal_stations"]:
        e["from_um"] = [1100.0, e["from_um"][1]]
        e["regs_um"] = [[(e["from_um"][0] + e["to_um"][0]) / 2, e["from_um"][1]]]
    return P


def test_plus_one_lane_stage_when_the_path_is_over_405_a_hop():
    P = plan_far()
    t = P["partition_types"][TN]
    r0 = R.regrid_type(TN, copy.deepcopy(t), P, R.COL_GAP, R.ROW_GAP, R.STRIP, add_stage=False)
    assert r0["result"] == "REFUSED hop" and r0["n_hop_over"] > 0, r0
    r = R.regrid_type(TN, t, P, R.COL_GAP, R.ROW_GAP, R.STRIP)
    assert r["result"] == "moved" and r["add_stage"] == {"ho": 1} and r["depth"] == {"ho": 2}, r
    assert r["worst_planned_hop_um"] <= R.HOP
    assert all(len(e["regs_um"]) == 2 and "S81-HI-STAGE" in e["note"] for e in t["internal_stations"])     # EVERY row of the class


def test_hop_fix_resites_then_grows():
    cores = [dict(inst="u_lf.u_vq", origin_um=[800.0, 800.0], orient="R0", outline_um=[100.0, 100.0])]
    mk = lambda to, reg: dict(bits=8, conn="bus:leafdn_i0", launch="face bus leafdn_i0", capture="u_lf.u_vs.s_d",      # noqa: E731
                              from_um=[100.0, 0.0], to_um=list(to), regs_um=[list(reg)], note="")
    before = [mk([100.0, 700.0], [100.0, 350.0]), mk([400.0, 900.0], [150.0, 450.0])]
    t = dict(outline_um=[1000.0, 1200.0], hard_cores=cores,
             internal_stations=[mk([100.0, 700.0], [300.0, 350.0]), mk([400.0, 900.0], [10.0, 450.0])])
    t["internal_stations"][1]["capture"] = "u_lf.u_vq.m_i"; before[1]["capture"] = "u_lf.u_vq.m_i"
    rep = R.fix_hops(t, before)
    a, b = t["internal_stations"]
    assert len(a["regs_um"]) == 1 and max(R._hops(a)) <= R.HOP                      # 550 -> re-sited, 0 cycles
    assert len(b["regs_um"]) == 2 and max(R._hops(b)) <= R.HOP                      # 1,200 um run: no one-station site, +1 station
    assert [g["capture"] for g in rep["grown"]] == ["u_lf.u_vq"] and not rep["left"]
    rep2 = R.fix_hops(t, before)                                                     # rows inside 405 are left alone
    assert not rep2["resited"] and not rep2["grown"]


def kv_plan():
    """a kv leaf: the plan of plan() plus one content macro (u_bound vp memory, contents[] with a lef) in the slot columns"""
    P = plan()
    t = P["partition_types"][TN]
    S, _ = R.find_slots(t)
    x, y = sorted(S["slots"])[len(S["slots"]) // 2]
    t["contents"] = [dict(inst="u_lf", module="m"),
                     dict(inst="u_bound.u_u_vp_u_b0", module="mem", lef="m.lef", origin_um=[x + 20.0, y + 30.0], outline_um=[169.368, 29.16], orient="R0")]
    return P, (x + 20.0, y + 30.0, x + 20.0 + 169.368, y + 30.0 + 29.16)


def test_content_macros_are_core_boxes():
    """S81-LEAF-REGRID CORE-BOX: kv_leaf t5 ln_11 was moved onto u_bound.u_u_vp_u_b0 / b1 (KITFIT-OVERLAP at the pre-bind
    gate): the re-grid read hard_cores only."""
    P, box = kv_plan()
    t = P["partition_types"][TN]
    free, _ = R.find_slots(plan()["partition_types"][TN])
    assert any(_hit(s, box, 0.0) for s in free["slots"])                 # mutant: without the macro a slot stands on it
    assert "u_bound.u_u_vp_u_b0" in [b[0] for b in H.boxes(t)] and "u_bound.u_u_vp_u_b0" in [b[0] for b in R.obox(t)]
    S, err = R.find_slots(t)
    assert err is None and S["slots"] and not any(_hit(s, box, R.OBS_GAP - 1e-6) for s in S["slots"])
    S2, _ = R.find_slots_2d(t, 16)
    assert not any(_hit(s, box, R.OBS_GAP - 1e-6) for s in S2["slots"])
    r = R.regrid_type(TN, t, P, R.COL_GAP, R.ROW_GAP, R.STRIP)
    assert r["result"] == "moved", r
    R.seat(t)
    c = R.check_type(TN, t)
    assert c["lanes_on_core"] == [] and c["sites_in_core"] == 0
    assert not any(_hit(tuple(b[1:3]), box, 0.0) for b in R.lbox(t))
    # the check refuses a lane put back on the macro
    ln = next(h for h in t["hard_cores"] if H.LN.search(h["inst"]))
    ln["origin_um"] = [box[0] - 30.0, box[1] - 40.0]
    c = R.check_type(TN, t)
    assert c["lanes_on_core"] == [ln["inst"]] and not c["pass"]


def test_clock_sites_inside_a_core_are_seated_and_counted():
    """J7 base 11-21: START relay stages and local resets (key xy_um) stood under the moved lanes; check read other keys
    (start_in_core 0 on 6,000 sites) and seat() left them."""
    P = plan()
    t = P["partition_types"][TN]
    ln = next(h for h in t["hard_cores"] if H.LN.search(h["inst"]))
    x, y = ln["origin_um"]
    inside, beside = [x + 50.0, y + 60.0], [x - 3.0, y + 60.0]
    t["clock"] = dict(landing_writer_start=dict(depth=2, branches=dict(ft0_o=dict(stages=[dict(xy_um=list(inside), raw_reset="r"), dict(xy_um=list(beside), raw_reset="r")]))),
                      landing_local_resets=[dict(name="fstart_0", raw="rst_rl_1", xy_um=list(inside), consumers=["c"])])
    assert R.check_type(TN, t)["start_in_core"] == 2
    mv = [m for m in R.seat(t) if m["kind"] == "clock_site"]
    assert len(mv) == 2 and R.check_type(TN, t)["start_in_core"] == 0
    st = t["clock"]["landing_writer_start"]["branches"]["ft0_o"]["stages"]
    assert st[1]["xy_um"] == beside and st[0]["raw_reset"] == "r"            # a site beside the core keeps its place
    for p in (st[0]["xy_um"], t["clock"]["landing_local_resets"][0]["xy_um"]):
        assert H.clear(p, H.boxes(t)) >= R.SEAT - 1e-6 and R.md(p, inside) < 80.0


def test_explicit_tap_table_under_a_lane_fails_the_check():
    """J7 gate 11-21: t21 / t25 / t37 carry frozen explicit tap tables; 27 taps stood under the moved lanes and the bind
    refused the plan after a 35-min elaboration.  The check now asks the bind's own rule."""
    P = plan()
    t = P["partition_types"][TN]
    ln = next(h for h in t["hard_cores"] if H.LN.search(h["inst"]))
    x, y = ln["origin_um"]
    t["clock"] = dict(tap_mode="explicit", taps=[dict(name="clk", xy=[50.0, 50.0]), dict(name="clk_t1", xy=[x + 40.0, y + 40.0])])
    c = R.check_type(TN, t)
    assert "clk_t1 violates" in c["explicit_tap_refused"] and not c["pass"]
    t["clock"]["taps"][1]["xy"] = [50.0, 150.0]
    assert R.check_type(TN, t)["explicit_tap_refused"] is None
    t["clock"]["tap_mode"] = "grid+explicit"; t["clock"]["taps"][1]["xy"] = [x + 40.0, y + 40.0]
    assert R.check_type(TN, t)["explicit_tap_refused"] is None                 # only a frozen explicit table is judged here


def _tapped(orient="R0"):
    """the synthetic leaf with a pin view (clk on the south edge) and one early core tap per lane, sited as early_core_taps.add does"""
    P = plan()
    t = P["partition_types"][TN]
    taps = []
    for h in t["hard_cores"]:
        if H.LN.search(h["inst"]):
            h["orient"] = orient
            h["pins"] = [dict(name="clk", layer="M3", x=29.133, y=0.019)]
            taps.append(dict(name=h["inst"] + ".clk", kind="core", xy=[0.0, 0.0], insertion_ps=260.0))
    t["clock"] = dict(core_taps="early", taps=taps)
    H.retap_lanes(t, {h["inst"] for h in t["hard_cores"]})
    return P, t


def _pin_dist(t):
    hc = {h["inst"]: h for h in t["hard_cores"]}
    return {tp["name"]: R.md(H.core_clk_pin(hc[tp["name"].rsplit(".", 1)[0]]), tp["xy"]) for tp in t["clock"]["taps"]}


def test_core_taps_are_derived_from_the_moved_core_not_shifted():
    """RG9 G0 11-21: 37 lane core taps outside the outline in 24 re-grid types (a lane moved to the west column at x 4.32
    took its tap, 9.6 um west of the core, to x -5.3), and t26 two taps on one M7 site."""
    for orient in ("R0", "MX"):
        P, t = _tapped(orient)
        ln = next(h for h in t["hard_cores"] if H.LN.search(h["inst"]))
        tp = next(a for a in t["clock"]["taps"] if a["name"] == ln["inst"] + ".clk")
        tp["xy"] = [ln["origin_um"][0] - 9.639, ln["origin_um"][1] + 0.031]           # the stale J7 form: legal only where it was
        r = R.regrid_type(TN, t, P, R.COL_GAP, R.ROW_GAP, R.STRIP)
        assert r["result"] == "moved" and r["move"]["core_taps"], r
        W, Ht = t["outline_um"]
        assert H.core_tap_errors(t) == [] and all(0 <= a["xy"][0] <= W and 0 <= a["xy"][1] <= Ht for a in t["clock"]["taps"])
        assert max(_pin_dist(t).values()) <= 4 * H.CORE_TAP_CLEAR                         # beside its own pin again
        B = [b for b in H.boxes(t)]
        assert not any(b[1] < a["xy"][0] < b[3] and b[2] < a["xy"][1] < b[4] for a in t["clock"]["taps"] for b in B)
        assert R.check_type(TN, t)["core_taps_bad"] == []


def test_check_fails_a_lane_core_tap_outside_the_outline_or_on_another_tap():
    P, t = _tapped()
    a, b = t["clock"]["taps"][0], t["clock"]["taps"][1]
    keep = list(a["xy"])
    a["xy"] = [-5.319, 400.0]
    c = R.check_type(TN, t)
    assert c["core_taps_bad"] == [[a["name"], "outside the outline"]] and not c["pass"]
    a["xy"] = list(b["xy"])
    assert {n for n, _ in R.check_type(TN, t)["core_taps_bad"]} == {a["name"], b["name"]}
    a["xy"] = keep
    assert R.check_type(TN, t)["core_taps_bad"] == []


def test_a_moved_lane_without_a_pin_view_keeps_a_legal_shifted_tap_and_refuses_an_illegal_one():
    P, t = _tapped()
    ln = next(h for h in t["hard_cores"] if H.LN.search(h["inst"]))
    tp = next(a for a in t["clock"]["taps"] if a["name"] == ln["inst"] + ".clk")
    del ln["pins"]
    x, y = ln["origin_um"]; was = list(tp["xy"])
    n = H.move_lanes(t, {ln["inst"]: dict(origin_um=[x, y - 4.32], orient="R0")}, 0)
    assert n["core_taps"] == [] and tp["xy"] == [was[0], round(was[1] - 4.32, 3)]
    tp["xy"] = [1.0, 1.0]
    try:
        H.move_lanes(t, {ln["inst"]: dict(origin_um=[x, y - 8.64], orient="R0")}, 0, near=0.0)
        H.move_lanes(t, {ln["inst"]: dict(origin_um=[x - 400.0, y - 8.64], orient="R0")}, 0)
        assert False, "a tap shifted out of the outline must stop the move"
    except SystemExit as e:
        assert "core taps of moved lanes are not legal" in str(e)


def test_nudge_moves_lanes_on_the_lattice_and_restores_a_refused_type():
    P, t = _tapped()
    r = R.regrid_type(TN, t, P, R.COL_GAP, R.ROW_GAP, R.STRIP)
    R.seat(t)
    assert r["result"] == "moved" and R.check_type(TN, t)["pass"]
    ls = sorted((h for h in t["hard_cores"] if H.LN.search(h["inst"])), key=lambda h: (h["origin_um"][0], h["origin_um"][1]))
    col = max(([h for h in ls if h["origin_um"][0] == x] for x in {h["origin_um"][0] for h in ls}), key=len)      # the fullest column
    room = col[0]["origin_um"][1] - R.EDGE
    assert room >= R.G, "fixture: the first column needs room below"
    was = {h["inst"]: list(h["origin_um"]) for h in col}
    n = R.nudge_type(TN, t, P, [h["inst"] for h in col], (0.0, -R.G))
    assert n["result"] == "moved" and n["check"]["pass"], n
    assert all(h["origin_um"] == [was[h["inst"]][0], round(was[h["inst"]][1] - R.G, 4)] for h in col)
    assert max(_pin_dist(t).values()) <= 4 * H.CORE_TAP_CLEAR and "S81-LEAF-NUDGE" in t["note"]
    keep = copy.deepcopy(t)
    assert R.nudge_type(TN, t, P, [col[0]["inst"]], (0.0, 1.0))["result"].startswith("REFUSED move")           # off the lattice
    assert len(col) >= 2, "fixture: the first column holds two lanes"
    dy = -(round((col[1]["origin_um"][1] - col[0]["origin_um"][1] - L) / R.G) - 1) * R.G                        # 4.32 um (or less) off the lane below
    bad = R.nudge_type(TN, t, P, [col[1]["inst"]], (0.0, dy))
    assert bad["result"].startswith("REFUSED") and t == keep
