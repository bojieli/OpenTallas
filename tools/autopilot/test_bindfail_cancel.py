"""WAVE-PILOT-FIX 11-18 (OWNER r705 (1)): under stops_off a bind / LATCHECK failure for named types cancels their running kits by exact unit and posts one line naming the owner lane; nothing is held."""
import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_apply as PA  # noqa: E402


def coord(tmp_path, stops_off=True, die="qc"):
    c = tmp_path / "coord"
    (c / "autopilot").mkdir(parents=True)
    (c / "bin").mkdir()
    (c / "bin/post.sh").write_text("#!/bin/bash\n")
    d = {"src": "/x/old", "event": "E0", "plan_sha256": "s1", "hold_event_items": {"s1": ["a", "b", "c"]}, "owner_lane": "QC-PLAN-R3 (Sonnet)", "die_owner": "DIE-QC-103"}
    cfg = {"dies": {die: d}}
    if stops_off:
        cfg["stops_off"] = True
    (c / "autopilot/kit_wave.json").write_text(json.dumps(cfg))
    st = {"items": {
        "k1": {"die": die, "item": "a", "status": "ENQUEUED", "q_status": "RUNNING", "kit": "epyc8:/w/items/a/attempt_2/gen/a", "unit": "kw-a-2"},
        "k2": {"die": die, "item": "b", "status": "RUNNING", "kit": "intel1:/w/items/b/attempt_1/gen/b", "unit": "kw-b-1"},
        "k3": {"die": die, "item": "c", "status": "FAIL", "kit": "epyc8:/w/items/c/attempt_1/gen/c", "unit": "kw-c-1"},      # not running: untouched
        "k4": {"die": die, "item": "z", "status": "RUNNING", "kit": "epyc8:/w/items/z/attempt_1/gen/z", "unit": "kw-z-1"}}}      # not named: untouched
    (c / "autopilot/kit_wave_state.json").write_text(json.dumps(st))
    return c


class Runner:
    def __init__(self):
        self.calls = []

    def __call__(self, argv, capture_output=True, text=True, timeout=0):
        self.calls.append(argv)
        out = ""
        if "--dry-run" in " ".join(argv):
            out = "oth-ubuntu-11-100\noth-ubuntu-12-100\n" if "/items/a/" in " ".join(argv) else "oth-ubuntu-21-200\n"
        return types.SimpleNamespace(returncode=0, stdout=out, stderr="")


def test_cancels_named_running_kits_by_exact_unit_posts_one_line_and_holds_nothing(tmp_path):
    c = coord(tmp_path)
    run = Runner()
    a = types.SimpleNamespace(coord=str(c), die="qc", lane="QC-PLAN-R3", id="n3", types="a,b,c", log=None, reason="", dry=False)
    assert PA.cmd_bind_fail(a, run=run) == 0
    joined = [" ".join(x) for x in run.calls]
    stops = [j for j in joined if "ot-heavy-stop --unit" in j]
    assert sorted(s.split("--unit ")[1] for s in stops) == ["oth-ubuntu-11-100", "oth-ubuntu-12-100", "oth-ubuntu-21-200"]
    assert any(j == "systemctl --user stop kw-b-1" for j in joined) and not any("kw-a-2" in j for j in joined if "systemctl" in j)   # a is an ENQUEUED job (no hub unit)
    assert not any("kw-c-1" in j or "kw-z-1" in j or "items/c/" in j or "items/z/" in j for j in joined)
    posts = [x for x in run.calls if x[:2] == ["bash", str(c / "bin/post.sh")]]
    assert len(posts) == 1 and "BIND-FAIL-CANCEL [QC-PLAN-R3 -> DIE-QC-103]" in posts[0][3] and "nothing is held" in posts[0][3]
    assert not any("kit_wave_edit" in j for j in joined)                                  # no hold record


def test_without_stops_off_the_hold_path_is_unchanged(tmp_path, capsys, monkeypatch):
    c = coord(tmp_path, stops_off=False)
    monkeypatch.setattr(PA.HR, "add_record", lambda cfg, die, rec: rec)
    a = types.SimpleNamespace(coord=str(c), die="qc", lane="L", id="n3", types="a", log=None, reason="", dry=True)
    assert PA.cmd_bind_fail(a) == 0
    assert json.loads(capsys.readouterr().out)[0]["value"][0]["items"] == ["a"]


def test_hbm_is_not_covered_by_stops_off(tmp_path, capsys, monkeypatch):
    c = coord(tmp_path, die="hbm")
    monkeypatch.setattr(PA.HR, "add_record", lambda cfg, die, rec: rec)
    a = types.SimpleNamespace(coord=str(c), die="hbm", lane="L", id="n3", types="a", log=None, reason="", dry=True)
    assert PA.cmd_bind_fail(a) == 0
    assert "value" in json.loads(capsys.readouterr().out)[0]                              # the hold patch, not a cancel plan


def test_dry_run_lists_what_would_be_cancelled(tmp_path, capsys):
    c = coord(tmp_path)
    a = types.SimpleNamespace(coord=str(c), die="qc", lane="L", id="n3", types="a,b", log=None, reason="", dry=True)
    assert PA.cmd_bind_fail(a, run=Runner()) == 0
    out = json.loads(capsys.readouterr().out)
    assert sorted(x[0] for x in out["cancel"]) == ["a", "b"] and out["owner"] == "DIE-QC-103"
