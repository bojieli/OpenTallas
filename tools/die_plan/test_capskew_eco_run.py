"""capskew_eco_run.py (CAPSKEW-ECO 11-17): selection, sizing, limits, exit codes and the wiring that keeps it opt-in."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import capskew_eco_run as C  # noqa: E402

SRC = (HERE / "capskew_eco_run.py").read_text()
INS = (HERE / "post_route_drv" / "capskew_eco_insert.tcl").read_text()
B, H = C.B, C.H


def test_step_is_the_smallest_that_covers_the_need_inside_the_hold_room():
    assert C.step_for(10, 100, 130) == ([B], 20.0)
    assert C.step_for(60, 100, 130)[0] == [H]
    assert C.step_for(97, 200, 130)[0] == [H, B, B]
    assert C.step_for(125, 200, 130)[0] == [H, H]


def test_hold_room_caps_the_step_and_a_partial_gain_is_taken():
    cells, d = C.step_for(97, 62 - 10, 130)          # room 52 ps: FF delay of 65 x 0.65 = 42 fits, 86 x 0.65 = 56 does not
    assert cells == [H] and d == 65.0
    assert C.step_for(10, 5, 130) == (None, 0.0)      # not even one BUFx4 fits


def test_per_flop_delay_cap():
    assert C.step_for(125, 500, 65)[1] == 65.0


def _tt(n, s):
    return {"u/pp1[%d]$_DFF_P_/D" % i: s - 0.1 * i for i in range(n)}


def test_plan_picks_failing_capture_flops_with_hold_room_and_skips_the_rest():
    tt = {"a/D": -105.0, "b/D": -60.0, "c/D": -5.0, "d/D": -50.0, "e/RESETN": -80.0, "f/D": -40.0}
    ff = {"b/D": 4.0, "f/D": 200.0}                  # b: room -6 -> no room; others unlisted = >= 150
    pl = C.plan(tt, ff, {})
    got = {i: d for i, s, n, c, d in pl["ck"]}
    assert set(got) == {"a", "d", "f"} and got["a"] == 107.0
    why = {p: w for w, p, s in pl["skipped"]}
    assert "no hold room" in why["b/D"] and "not a flop D pin" in why["e/RESETN"] and "c/D" not in why


def test_launch_side_room_is_respected_when_the_sta_reports_it():
    pl = C.plan({"a/D": -50.0}, {}, {"a/QN": 40.0})
    assert pl["ck"] == [] and "launch side" in pl["skipped"][0][0]
    assert len(C.plan({"a/D": -50.0}, {}, {"a/QN": 400.0})["ck"]) == 1


def test_broken_hold_gets_a_pad_and_needs_setup_room():
    pl = C.plan({"a/D": 300.0, "b/D": 40.0}, {"a/D": -15.0, "b/D": -2.0}, {})
    pads = {(i): c for i, p, h, c in pl["pads"]}
    assert pads["a"] == [H] and pads["b"] == [B]        # -15 -> +8 needs 23 ps: HB4 (33); b: 40 - 20 ok -> BUFx4 for need 10
    assert "b" in {i for i, p, h, c in C.plan({"b/D": 40.0}, {"b/D": -2.0}, {})["pads"]}


def test_gain_limit_counts_the_unfixed_worst_endpoint():
    pl = C.plan({"a/D": -105.0, "b/D": -100.0}, {"a/D": 5.0}, {})   # a has no hold room -> unfixed, stays the worst
    assert pl["unfixed"] == 1 and pl["worst_after_pred"] == -105.0
    assert any(v.startswith("setup_gain") for v in C.check_limits(pl))
    ok = C.plan({"a/D": -105.0, "b/D": -100.0}, {}, {})
    assert C.check_limits(ok) == [] and ok["gain_pred"] >= 0.7 * ok["deficit"]


def test_sd9f_shape_is_inside_the_limits():
    tt = {"u/pp1[%d]/D" % i: -105.0 + 80 * i / 201 for i in range(202)}
    pl = C.plan(tt, {}, {})
    assert len(pl["ck"]) == 202 and C.check_limits(pl) == []
    assert sum(len(c[3]) for c in pl["ck"]) >= 202


def test_flop_and_pad_count_limits():
    pl = C.plan(_tt(310, -60.0), {}, {})
    assert any(v.startswith("capture_flops 310 > 300") for v in C.check_limits(pl))
    assert C.check_limits(pl, max_flops=400) == []
    pads = C.plan({}, {"p%d/D" % i: -5.0 for i in range(101)}, {})
    assert any(v.startswith("hold_pads 101") for v in C.check_limits(pads))


def test_measured_gain_rule():
    assert C.measured_gain(-105.6, -20.79)[0] is True       # 84.8 >= 0.7 x 105.6
    assert C.measured_gain(-105.6, -50.0)[0] is False


def test_list_rows_and_tsv_reader(tmp_path):
    pl = C.plan({"a/D": -50.0, "b/D": 100.0}, {"b/D": -3.0}, {})
    rows = C.list_rows(pl).splitlines()
    assert rows[0] == "CK\ta\tCLK\t" + ",".join(pl["ck"][0][3]) and rows[1].startswith("D\tb\tD\t")
    p = tmp_path / "x.tsv"
    p.write_text("h\th\na/D\t-1.5\na/D\t-3\nb/D\tnan\nc/D\tx\n")
    assert C.read_tsv(p) == {"a/D": -3.0}


def test_nothing_to_do_plan_is_empty():
    pl = C.plan({"a/D": 50.0}, {"a/D": 40.0}, {})
    assert pl["ck"] == [] and pl["pads"] == []


def test_session_patch_adds_the_right_block_once_and_refuses_a_foreign_session():
    s = "a\n" + C.MARK + "\nb\n"
    tt, ff = C.patch_session(s, "tt"), C.patch_session(s, "ff")
    assert "cs_tt.tsv" in tt and "cs_ff.tsv" not in tt and "cs_ff.tsv" in ff and tt.count(C.MARK) == 1
    try:
        C.patch_session("none", "tt")
        raise AssertionError("must refuse")
    except SystemExit:
        pass


def test_limits_and_exit_codes_are_wired():
    assert SRC.count("return finish(4,") >= 1 and "return refuse(" in SRC
    assert "return finish(2," in SRC and "return finish(0 if code == 0 else 1," in SRC and SRC.count("return finish(3,") >= 5
    assert "getObstructions" in (HERE / "post_route_drv" / "capskew_eco_route.tcl").read_text() and "obs_in != obs_out" in SRC
    for tok in ("clock root/port net", "clock tap net", "not a leaf"):
        assert tok in INS
    assert INS.index("CAPSKEW_REFUSED") < INS.index("odb::dbInst_create")          # limits before any change
    assert "never overwrite a previous ECO" in SRC and "never opened for writing" in SRC


def test_eco_loop_hook_is_opt_in_and_off_by_default():
    import eco_loop as E
    assert E.capskew_enabled({}) is False and E.capskew_enabled({"OT_CAPSKEW_ECO": "0"}) is False
    assert E.capskew_enabled({"OT_CAPSKEW_ECO": "1"}) is True
    rec = {"checks": {"setup_tt": {"verdict": "FAIL", "wns_ps": -105.6}, "hold_ff": {"verdict": "PASS"}, "drc": {"verdict": "PASS", "count": 0}}}
    assert E.capskew_case(rec) is True
    rec["checks"]["drc"] = {"verdict": "FAIL", "count": 3}
    assert E.capskew_case(rec) is False
    assert E.capskew_case({}) is False
