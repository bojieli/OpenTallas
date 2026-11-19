"""START-RAW-RESITE-1: a START stage on a far pad tap takes the nearest same-depth tap relay (FABLE-FIX-KV-HG 11-18)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import start_stage_raw_resite as S

TREE = {"tree": {"relays": [
    {"name": "u_rrl_52", "xy": [631.8, 1503.4], "q": "rst_n_t74", "depth": 9, "tap": 74, "kind": "pad"},
    {"name": "u_rrl_9", "xy": [17.8, 17.3], "q": "rst_n_t1", "depth": 9, "tap": 1, "kind": "tap"},
    {"name": "u_rrl_8", "xy": [27.0, 230.6], "q": "rst_n_t7", "depth": 9, "tap": 7, "kind": "pad"},
    {"name": "u_rrl_7", "xy": [10.0, 30.0], "q": "rst_n_t5", "depth": 8, "tap": 5, "kind": "tap"},
    {"name": "u_rrl_6", "xy": [5.0, 21.0], "q": "rst_rl_6", "depth": 9, "tap": 1, "kind": "tap"},
    {"name": "u_rrl_5", "xy": [6.0, 22.0], "q": "rst_n_t2", "depth": 9, "tap": 2, "kind": "tap"}]}}
R = S.relay_table(TREE)


def test_far_pad_tap_takes_nearest_same_depth_tap():
    assert S.pick("rst_n_t74", [4.32, 20.064], R, set(), 405.0)[::2] == ("rst_n_t2", "resited")
    # a ported relay is never picked; the next one is
    assert S.pick("rst_n_t74", [4.32, 20.064], R, {"rst_n_t2"}, 405.0)[::2] == ("rst_n_t1", "resited")


def test_in_reach_unknown_and_wrong_depth_are_left():
    assert S.pick("rst_n_t7", [4.32, 249.536], R, set(), 405.0)[::2] == ("rst_n_t7", None)
    assert S.pick("rst_rl_999", [0, 0], R, set(), 405.0) == ("rst_rl_999", None, None)
    # only depth 8 and a non-tap relay are near: nothing qualifies
    only = {k: v for k, v in R.items() if k in ("rst_n_t74", "rst_n_t5", "rst_rl_6")}
    assert S.pick("rst_n_t74", [4.32, 20.064], only, set(), 405.0)[::2] == ("rst_n_t74", "unresolved")


def test_plan_roundtrip(tmp_path):
    plan = {"partition_types": {"t": {"clock": {"landing_writer_start": {"depth": 2, "branches": {"ft0_o": {"stages": [
        {"xy_um": [4.32, 249.536], "raw_reset": "rst_n_t7"}, {"xy_um": [4.32, 20.064], "raw_reset": "rst_n_t74"}]}}}}}}}
    p = tmp_path / "plan.json"; p.write_text(json.dumps(plan, indent=2))
    b = tmp_path / "rtl"; b.mkdir(); (b / "t_part.reset_tree.json").write_text(json.dumps(dict(TREE, plan_type="t")))
    (b / "t_part.sv").write_text("assign rst_o_0 = rst_n_t2;\n")
    out, rep = tmp_path / "o.json", tmp_path / "r.json"
    assert S.main([str(p), str(b), "--out", str(out), "--report", str(rep)]) == 0
    st = json.loads(out.read_text())["partition_types"]["t"]["clock"]["landing_writer_start"]["branches"]["ft0_o"]["stages"]
    assert [s["raw_reset"] for s in st] == ["rst_n_t7", "rst_n_t1"]
    r = json.loads(rep.read_text())
    assert len(r["resited"]) == 1 and r["resited"][0]["was"] == "rst_n_t74" and r["resited"][0]["stage"] == 1
    # the fixed plan passes the check and is written back byte-identical
    assert S.main([str(out), str(b), "--check"]) == 0
    out2 = tmp_path / "o2.json"
    assert S.main([str(out), str(b), "--out", str(out2)]) == 0 and out2.read_text() == out.read_text()
    assert S.main([str(p), str(b), "--check"]) == 1
