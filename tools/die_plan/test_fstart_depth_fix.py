"""FSTART-DEPTH-CLASS: fstart_depth_fix.py pure parts (classify / pick / repick_type / type_ops / apply_ops) on synthetic
types, plus the generator rule it asks (clock_landings._local_resets 'release edge would move') parsed by MISMATCH."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fstart_depth_fix as F  # noqa: E402


def _c(ok, old=None, od=None, cd=None, raw="rst_rl_1", red=None, err=None):
    return dict(ok=ok, old=old, old_depth=od, copy_depth=cd, raw=raw, rederived_from=red, error=err)


def _tree():
    rel = [dict(q="rst_rl_1", depth=7, xy=[100.0, 100.0]),
           dict(q="rst_rl_2", depth=8, xy=[150.0, 100.0]),     # 50 um from the leaf
           dict(q="rst_rl_3", depth=8, xy=[110.0, 100.0]),     # 10 um, but ported
           dict(q="rst_rl_4", depth=8, xy=[120.0, 100.0]),     # 20 um, name collides with an anchor row of another depth
           dict(q="rst_rl_5", depth=8, xy=[600.0, 100.0]),
           dict(q="rst_n_t3", depth=9, xy=[100.0, 100.0])]
    return dict(relays=rel)


def _type():
    return dict(clock=dict(
        landing_local_resets=[dict(name="fstart_1", raw="rst_rl_1", xy_um=[100.0, 100.0], consumers=["u_cland_origin"]),
                              dict(name="fstart_0", raw="rst_rl_9", xy_um=[0.0, 0.0], consumers=["u_cland_fstart_ft0_o"])],
        reset_tree_anchor=dict(inputs=dict(taps="x"), tol_um=300.0,
                               relays=dict(rst_rl_1=dict(depth=7, xy=[100.0, 100.0]), rst_rl_9=dict(depth=8, xy=[0.0, 0.0]),
                                           rst_rl_4=dict(depth=6, xy=[1.0, 1.0])))))


def test_mismatch_regex_matches_the_generator_message():
    msg = ("col_h9_r0_p5__t1__pvbca8d846: landing_local_resets.fstart_1: consumer u_cland_origin reset rst_n_t38 depth 9 != "
           "copy depth 8 (raw rst_rl_24): release edge would move")
    m = F.MISMATCH.search(msg)
    assert m and m.groups() == ("fstart_1", "u_cland_origin", "rst_n_t38", "9", "8", "rst_rl_24")


def test_generator_message_format_unchanged():
    src = (Path(__file__).resolve().parent / "clock_landings.py").read_text()
    assert 'f"copy depth {depth(raw) + 1} (raw {raw}): release edge would move"' in src
    assert 'consumer {c} reset {old} depth {depth(old)} != "' in src


def test_classify():
    probe = {
        "a": dict(raw="r", plan_raw="r", consumers={"c1": _c(True, cd=9)}),
        "b": dict(raw="r", plan_raw="r", consumers={"c1": _c(False, "rst_n_t38", 9, 8)}),
        "c": dict(raw="r", plan_raw="r", consumers={"c1": _c(False, "x", 9, 8), "c2": _c(False, "y", 10, 8)}),
        "d": dict(raw="r", plan_raw="r", consumers={"c1": _c(False, err="raw 'r' has no registered wavefront driver")}),
        "e": dict(raw="r2", plan_raw="r", consumers={"c1": _c(True, cd=9)}),
        "f": dict(raw="r", plan_raw="r", consumers={"c1": _c(True, cd=9, red="r0")}),
        "g": dict(raw="r", plan_raw="r", consumers={"c1": _c(False, "x", 9, 8), "c2": _c(True, cd=8)}),
    }
    rows = F.classify(probe)
    assert rows["a"]["cls"] == "OK"
    assert rows["b"]["cls"] == "MISMATCH" and rows["b"]["need_depth"] == 8
    assert rows["c"]["cls"] == "SPLIT" and rows["c"]["need_depths"] == [8, 9]
    assert rows["d"]["cls"] == "OTHER"
    assert rows["e"]["cls"] == "SAME-DEPTH" and rows["f"]["cls"] == "SAME-DEPTH"
    assert rows["g"]["cls"] == "SPLIT"           # an OK consumer pins the current depth: no single raw serves both


def test_pick_skips_ported_colliding_and_far():
    t = _tree()
    anc = _type()["clock"]["reset_tree_anchor"]["relays"]
    q, r, d = F.pick([100.0, 100.0], 8, t["relays"], {"rst_rl_3"}, 300.0, anc)
    assert q == "rst_rl_2" and d == 50.0
    q, r, d = F.pick([100.0, 100.0], 8, t["relays"], {"rst_rl_3", "rst_rl_2"}, 300.0, anc)
    assert q is None and r["q"] == "rst_rl_5" and d == 500.0
    q, _r, _d = F.pick([100.0, 100.0], 9, t["relays"], set(), 300.0, anc)
    assert q is None                              # rst_n_t<k> is never a raw (rst_rl_<k> only)


def test_repick_type_ops_roundtrip_and_idempotent():
    tn, t, tree = "col_x", _type(), _tree()
    rows = F.classify({"fstart_1": dict(raw="rst_rl_1", plan_raw="rst_rl_1", xy_um=[100.0, 100.0],
                                        consumers={"u_cland_origin": _c(False, "rst_n_t38", 9, 8, raw="rst_rl_1")}),
                       "fstart_0": dict(raw="rst_rl_9", plan_raw="rst_rl_9", xy_um=[0.0, 0.0],
                                        consumers={"u_cland_fstart_ft0_o": _c(True, cd=9, raw="rst_rl_9")})})
    ck, reps, unfixed = F.repick_type(tn, t, rows, tree, {"rst_rl_3"}, 300.0)
    assert not unfixed and len(reps) == 1
    x = reps[0]
    assert (x["cls"], x["old_raw"], x["new_raw"], x["new_depth"], x["copy_depth"]) == ("DEPTH-CHANGE", "rst_rl_1", "rst_rl_2", 8, 9)
    assert x["start_release_ok"] and x["consumers"]["u_cland_origin"]["reset_depth"] == 9
    rel = ck["reset_tree_anchor"]["relays"]
    assert "rst_rl_1" not in rel and rel["rst_rl_2"] == dict(depth=8, xy=[150.0, 100.0]) and "rst_rl_9" in rel
    assert rel["rst_rl_4"] == dict(depth=6, xy=[1.0, 1.0])    # unrelated rows untouched
    assert ck["reset_tree_anchor"]["inputs"] == dict(taps="x")
    ops = F.type_ops(tn, t["clock"], ck)
    paths = {o["path"]: o for o in ops}
    assert paths[f"/partition_types/{tn}/clock/landing_local_resets/0/raw"]["old"] == "rst_rl_1"
    assert paths[f"/partition_types/{tn}/clock/reset_tree_anchor/relays/rst_rl_1"]["op"] == "remove"
    assert paths[f"/partition_types/{tn}/clock/reset_tree_anchor/relays/rst_rl_2"]["op"] == "add"
    plan = dict(partition_types={tn: copy.deepcopy(t)})
    n, noop, conf = F.apply_ops(plan, ops)
    assert (n, noop, conf) == (3, 0, [])
    assert plan["partition_types"][tn]["clock"] == ck
    n, noop, conf = F.apply_ops(plan, ops)       # second apply: all no-ops
    assert (n, noop, conf) == (0, 3, [])


def test_apply_refuses_a_changed_old_value():
    tn, t = "col_x", _type()
    ops = [dict(op="replace", path=f"/partition_types/{tn}/clock/landing_local_resets/0/raw", old="rst_rl_77", value="rst_rl_2")]
    plan = dict(partition_types={tn: copy.deepcopy(t)})
    n, noop, conf = F.apply_ops(plan, ops)
    assert n == 0 and conf and conf[0]["why"] == "old-value mismatch"
    assert plan["partition_types"][tn] == t


def test_old_anchor_row_kept_while_still_referenced():
    tn, t, tree = "col_x", _type(), _tree()
    t["clock"]["landing_reader_start"] = dict(branches=dict(ft0_i=dict(stages=[dict(raw_reset="rst_rl_1")])))
    rows = F.classify({"fstart_1": dict(raw="rst_rl_1", plan_raw="rst_rl_1", xy_um=[100.0, 100.0],
                                        consumers={"u_cland_origin": _c(False, "rst_n_t38", 9, 8)})})
    ck, reps, _u = F.repick_type(tn, t, rows, tree, set(), 300.0)
    assert reps[0]["new_raw"] == "rst_rl_3"
    assert "rst_rl_1" in ck["reset_tree_anchor"]["relays"]       # the START stage still names it


def test_split_and_no_candidate_are_unfixed():
    tn, t, tree = "col_x", _type(), _tree()
    rows = F.classify({"fstart_1": dict(raw="rst_rl_1", plan_raw="rst_rl_1", xy_um=[100.0, 100.0],
                                        consumers={"a": _c(False, "x", 9, 8), "b": _c(False, "y", 11, 8)}),
                       "fstart_0": dict(raw="rst_rl_9", plan_raw="rst_rl_9", xy_um=[0.0, 0.0],
                                        consumers={"c": _c(False, "z", 13, 9)})})
    ck, reps, unfixed = F.repick_type(tn, t, rows, tree, set(), 300.0)
    assert not reps and {u["cls"] for u in unfixed} == {"SPLIT", "NO-CANDIDATE"}
    assert ck == t["clock"]
