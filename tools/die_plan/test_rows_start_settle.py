import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rows_start_settle as R  # noqa: E402


def _side():
    return {"count_aligned": {"root_settle_cycles": 64},
            "collector": {"root": "r", "reset_max_release": 205,
                          "boot_budget": {"ring_train_max_cycles": 21, "raw_reset_release_max_cycles": 205, "ready_at_glue_max_cycles": 300,
                                          "local_registered_depths": {"r": 21, "a": 5}},
                          "edges": [{"src": "a", "dst": "r", "seam": True, "boot_transport_extra_cycles": 3}]}}


def test_row_derives_release_ready_and_settle_from_plan(tmp_path, monkeypatch):
    import reset_tree as RT
    import schema as S
    monkeypatch.setattr(S, "Plan", lambda raw, path: object())
    monkeypatch.setattr(RT, "wf_plan", lambda P: {"max_release": 464})
    (tmp_path / "side.json").write_text(json.dumps(_side()))
    (tmp_path / "ab.json").write_text(json.dumps({"clock_landing_table": "side.json"}))
    (tmp_path / "in.json").write_text(json.dumps({"clock": {"landing_network": {"count_aligned_bind": {"root_settle_cycles": 64}}}}))
    monkeypatch.chdir(tmp_path)
    assert R.main(["in.json", "out.json", "rep.json", "--asbuilt", "ab.json"]) == 0
    need = 464 + 21 + 5 + 21 + 21
    side = json.loads((tmp_path / "side.json").read_text())
    assert side["count_aligned"]["root_settle_cycles"] == need
    assert side["collector"]["boot_budget"]["raw_reset_release_max_cycles"] == 464 == side["collector"]["reset_max_release"]
    assert side["collector"]["boot_budget"]["ready_at_glue_max_cycles"] == need
    out = json.loads((tmp_path / "out.json").read_text())
    assert out["clock"]["landing_network"]["count_aligned_bind"]["root_settle_cycles"] == need
    import plan_gate_pre as G
    assert G.check_startsettle(str(tmp_path), "u", str(tmp_path / "side.json"), None, max_release=464) == []
