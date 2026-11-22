import json

import item_env_moves_gate as M


def _type():
    return {"outline_um": [1400.0, 1300.0], "hard_cores": [
        {"inst": "u_r0.u_c3_6", "origin_um": [1088.64, 544.32], "outline_um": [38.04, 62.952]},
        {"inst": "u_r0.u_e3.u_w", "origin_um": [578.88, 648.0], "outline_um": [268.38, 221.4]},
        {"inst": "u_r0.u_e3.u_e", "origin_um": [847.26, 648.0], "outline_um": [268.38, 221.4]},
        {"inst": "u_r0.u_e1", "origin_um": [10.0, 10.0], "outline_um": [100.0, 100.0]}]}


STALE = "u_r0.u_e1:596.16:216.0,u_r0.u_e3:596.16:604.8"
FIXED = "u_r0.u_e1:596.16:216.0"


def test_stale_split_group_move_fails_like_gen():
    cfg = {"item_env": {"col_p1__t1__pv*": {"OT_MACRO_MOVES": STALE}}}
    rows = M.check(cfg, {"col_p1__t1__pvA": _type(), "col_p1__t1__pvB": _type()})
    assert [r[1] for r in rows] == ["FAIL", "FAIL"]
    assert "overlap u_r0.u_c3_6 / u_r0.u_e3.u_e" in rows[0][2]


def test_exact_key_wins_over_glob():
    cfg = {"item_env": {"col_p1__t1__pv*": {"OT_MACRO_MOVES": STALE}, "col_p1__t1__pvA": {"OT_MACRO_MOVES": FIXED}}}
    rows = dict((r[0], r[1]) for r in M.check(cfg, {"col_p1__t1__pvA": _type(), "col_p1__t1__pvB": _type()}))
    assert rows == {"col_p1__t1__pvA": "PASS", "col_p1__t1__pvB": "FAIL"}


def test_types_without_moves_or_cores_are_skipped_and_prefix_filters():
    cfg = {"item_env": {"a*": {"OT_MACRO_MOVES": FIXED}}}
    types = {"a1": _type(), "a2": {"outline_um": [1, 1]}, "b1": _type()}
    assert [r[0] for r in M.check(cfg, types)] == ["a1"]
    assert M.check(cfg, types, prefix="b") == []


def test_main_proposed_row_clears_the_fail(tmp_path):
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps({"partition_types": {"col_p1__t1__pvA": _type()}}))
    conf = tmp_path / "kw.json"
    conf.write_text(json.dumps({"dies": {"s81": {"item_env": {"col_p1__t1__pv*": {"OT_MACRO_MOVES": STALE}}}}}))
    base = ["--config", str(conf), "--die", "s81", "--plan", str(plan)]
    assert M.main(base) == 1
    assert M.main(base + ["--moves", f"col_p1__t1__pv*={FIXED}"]) == 0
    assert M.main(["--config", str(tmp_path / "missing.json"), "--die", "s81", "--plan", str(plan)]) == 2
