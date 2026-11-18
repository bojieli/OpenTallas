import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW


class AP:
    DRY = True
    HUB_NAME = "hub"
    logs = []
    log = staticmethod(lambda m: AP.logs.append(m))
    sh = staticmethod(lambda *a, **k: (0, "", ""))


def mk(blocks):
    cfg = {"dies": {"s": {"enabled": True, "event": "e2", "plan": "/p.json", "gen_host": "h"}}}
    st = {"plans": ({"h:/p.json|e2": {"blocks": blocks}} if blocks is not None else {}),
          "adopt_seen": {"s": {"switched": True}},
          "items": {"a": {"die": "s", "item": "a", "event": "e1", "status": "RUNNING", "unit": "u", "block_sha": "b1", "dir": "/nonexistent"},
                    "b": {"die": "s", "item": "b", "event": "e1", "status": "RUNNING", "unit": "u", "block_sha": "b2", "dir": "/nonexistent"}}}
    return cfg, st


def test_only_the_item_whose_block_changed_is_cancelled():
    cfg, st = mk({"a": "b1", "b": "bX"})
    KW.supersede_on_switch(AP, cfg, st, {})
    assert st["items"]["a"]["status"] == "RUNNING" and st["items"]["b"]["status"] == "CANCELLED"


def test_nothing_is_cancelled_before_the_new_plan_is_probed():
    cfg, st = mk(None)
    KW.supersede_on_switch(AP, cfg, st, {})
    assert [r["status"] for r in st["items"].values()] == ["RUNNING", "RUNNING"]
    st["plans"]["h:/p.json|e2"] = {"blocks": {"a": "b1", "b": "bX"}}            # probe arrives: the window is still open
    KW.supersede_on_switch(AP, cfg, st, {})
    assert st["items"]["b"]["status"] == "CANCELLED" and st["items"]["a"]["status"] == "RUNNING"


def test_a_tree_rename_that_only_moves_paths_keeps_the_row():
    cfg, st = mk({"a": "bNEW", "b": "bX"})
    st["plans"]["h:/p.json|e2"]["norm_blocks"] = {"a": "n1", "b": "nX"}
    st["items"]["a"]["norm_block"] = "n1"                                  # raw block differs (tree name in a path), normalized is equal
    KW.supersede_on_switch(AP, cfg, st, {})
    assert st["items"]["a"]["status"] == "RUNNING" and st["items"]["b"]["status"] == "CANCELLED"


def test_probe_normalizes_tree_paths_and_hashes_file_content(tmp_path):
    import subprocess, json as _j
    for name, body in (("src_x_a", "same"), ("src_x_b", "same")):
        (tmp_path / name / "plan").mkdir(parents=True)
        (tmp_path / name / "plan" / "sink.json").write_text(body)
    def run(tree):
        plan = {"partition_types": {"t": {"clock": {"sink_bins_file": f"{tmp_path}/{tree}/plan/sink.json"}}}}
        (tmp_path / "plan.json").write_text(_j.dumps(plan))
        script = KW.PROBE_PLAN
        rr = subprocess.run(["python3", "-I", "-c", script, _j.dumps({"plan": str(tmp_path / "plan.json")})], capture_output=True, text=True)
        out = rr.stdout
        assert out.strip(), rr.stderr[-500:]
        return _j.loads(out.split("AP_JSON ", 1)[1])
    a, b = run("src_x_a"), run("src_x_b")
    assert a["blocks"]["t"] != b["blocks"]["t"] and a["norm_blocks"]["t"] == b["norm_blocks"]["t"]
    (tmp_path / "src_x_b" / "plan" / "sink.json").write_text("different")
    assert run("src_x_b")["norm_blocks"]["t"] != a["norm_blocks"]["t"]


def test_remote_stop_is_detached_and_config_autocommit_commits_a_dirty_valid_file(tmp_path):
    import subprocess as sp, json as _j
    started = []
    class A:
        DRY = False
        HUB_NAME = "hub"
        AP_DIR = str(tmp_path)
        COORD = str(tmp_path)
        log = staticmethod(lambda m: None)
    orig = KW.subprocess.Popen
    KW.subprocess.Popen = lambda *a, **k: started.append((a, k))
    try:
        assert KW.stop_on_fleet_bg(A, ["/r/a", "/r/a", ""]) == {}
    finally:
        KW.subprocess.Popen = orig
    assert len(started) == 1 and started[0][1]["start_new_session"] and "stop-bg" in started[0][0][0] and _j.loads(started[0][0][0][-2]) == ["/r/a"]
    calls = []
    def run(cmd, **k):
        calls.append(cmd)
        class R:
            returncode = 1 if "diff" in cmd else 0
            stdout = "/git"
            stderr = ""
        return R
    (tmp_path / KW.CFG_REL).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / KW.CFG_REL).write_text("{}")
    assert KW.auto_commit_config(A, run=run) == "committed" and any("coord-commit.sh" in str(c) for c in calls)
    (tmp_path / KW.CFG_REL).write_text("{bad")
    calls.clear()
    assert KW.auto_commit_config(A, run=run).startswith("skipped") and not any("coord-commit.sh" in str(c) for c in calls)


def test_signed_row_on_an_equivalent_normalized_block_is_not_relaunched():
    cfg, st = mk({"a": "bNEW"})
    st["plans"]["h:/p.json|e2"]["norm_blocks"] = {"a": "n1"}
    st["items"] = {"s": {"die": "s", "item": "a", "event": "e1", "status": "ENQUEUED", "q_status": "SIGNED", "block_sha": "bOLD", "norm_block": "n1"}}
    assert KW.signed_equivalent(cfg, st, "s", "a") is st["items"]["s"]
    st["items"]["s"]["norm_block"] = "n2"
    assert KW.signed_equivalent(cfg, st, "s", "a") is None
    st["items"]["s"].update(norm_block="n1", q_status="FAIL")
    assert KW.signed_equivalent(cfg, st, "s", "a") is None
