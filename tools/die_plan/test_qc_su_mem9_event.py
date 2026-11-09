import json
import pytest
import qc_su_mem9_event as E


def plan(ans=4):
    lanes = {"sl_W0_su_l0__x_su_l0_su_c": {"cycles": 5}, "sl_W0_su_l1__x_su_l1_su_c_p1": {"cycles": 5},
             "sl_W0_su_c__x_su_c_su_l0": {"cycles": ans}, "sl_E1_su_c__x_su_c_su_l1_p1": {"cycles": ans}}
    hc = [{"inst": f"u_lane{l}", "module": f"qfd_qc_su_lane_w_l{l}",
           "bound_group": {"kind": "exact_post_bind_group", "memory_alignment": 3, "kv_wr_pipe": 1}} for l in range(8)]
    return {"latency": {"lanes": lanes}, "partition_types": {"t": {"hard_cores": hc}}}


def run(tmp_path, d, *args):
    p = tmp_path / "p.json"
    p.write_text(json.dumps(d))
    o = tmp_path / "o.json"
    E.main([str(p), str(o), *args])
    return json.loads(o.read_text())


def test_extra_follows_plan_depths(tmp_path):
    out = run(tmp_path, plan(4), "--expect-extra", "9")
    assert {h["bound_group"]["memory_read_extra"] for h in out["partition_types"]["t"]["hard_cores"]} == {9}


def test_relay_event_changes_extra(tmp_path):
    out = run(tmp_path, plan(7))
    assert {h["bound_group"]["memory_read_extra"] for h in out["partition_types"]["t"]["hard_cores"]} == {12}
    with pytest.raises(SystemExit):
        run(tmp_path / "x" if (tmp_path / "x").mkdir() else tmp_path / "x", plan(7), "--expect-extra", "9")


def test_non_uniform_refused(tmp_path):
    d = plan(4)
    d["latency"]["lanes"]["sl_E1_su_c__x_su_c_su_l1_p1"]["cycles"] = 7
    with pytest.raises(SystemExit):
        run(tmp_path, d)
