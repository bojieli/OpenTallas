"""GOAL-MARK-1122 (COORD 18:4x/19:0x): a stale 'FAIL_PREFLOOR stage resume: goal X unsupported' marker no longer blocks the resume
of a placed private kit, and a private run-item drives from rt/current's kit_wave.py (TAPHOLD stopped after AUTO-GEOM on a pinned rt)."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW                                   # noqa: E402
from test_flow_privspec_r1 import chain_fixture          # noqa: E402

GOAL_LINE = "FAIL_PREFLOOR stage resume: goal finish unsupported"


def _clear(kit):
    return subprocess.run(["bash", "-c", KW.stale_goal_mark_cmd(str(kit))], capture_output=True, text=True, check=True).stdout


def test_goal_only_marker_is_moved_aside(tmp_path):
    (tmp_path / "FAIL_PREFLOOR").write_text(GOAL_LINE + "\n" + GOAL_LINE + "\n\n")
    assert "KW_CHAIN_GOAL_MARK CLEARED" in _clear(tmp_path)
    assert not (tmp_path / "FAIL_PREFLOOR").exists()
    kept = list(tmp_path.glob("FAIL_PREFLOOR.goal_unsupported.*"))
    assert len(kept) == 1 and GOAL_LINE in kept[0].read_text()


def test_marker_with_any_real_failure_is_kept(tmp_path):
    (tmp_path / "FAIL_PREFLOOR").write_text(GOAL_LINE + "\nFAIL_PREFLOOR LEC NOT EQUIVALENT\n")
    assert "KW_CHAIN_GOAL_MARK KEPT" in _clear(tmp_path)
    assert (tmp_path / "FAIL_PREFLOOR").exists()
    (tmp_path / "FAIL_PREFLOOR").write_text("FAIL_PREFLOOR stage resume: resume.json unreadable\n")
    assert "KEPT" in _clear(tmp_path)
    empty = tmp_path / "e"
    empty.mkdir()
    assert "KEPT" in _clear(empty)                     # no marker: nothing to move


def _probe(marks):
    return {"exists": True, "config": True, "routed": [], "signoff_dirs": [], "fail_marks": marks, "fail_text": {m: GOAL_LINE for m in marks},
            "runner": "/srv/w/items/t/gen/run_kit.sh", "signoff_goals": ["route"], "signoff_missing": []}


def test_chain_clears_stale_goal_mark_and_continues(tmp_path, monkeypatch):
    sp, res, out, run, fail, popen, wait, calls, popens, waits, K = chain_fixture(tmp_path, monkeypatch, probe=_probe(["FAIL_PREFLOOR"]))

    def run2(stage, argv, timeout=None, idempotent=False):
        if stage == "chain_clear_goal_mark":
            calls.append((stage, argv))
            return 0, "KW_CHAIN_GOAL_MARK CLEARED\n"
        return run(stage, argv, timeout=timeout, idempotent=idempotent)
    rc = KW.private_chain(sp, res, out, "route", run2, fail, {}, popen=popen, wait=wait, sleep=lambda s: None)
    assert rc == 0 and res["verdict"] == "SIGNED" and popens
    assert [c[0] for c in calls].index("chain_clear_goal_mark") < [c[0] for c in calls].index("chain_receipt")


def test_chain_still_refuses_a_kept_marker(tmp_path, monkeypatch):
    sp, res, out, run, fail, popen, wait, calls, popens, waits, K = chain_fixture(tmp_path, monkeypatch, probe=_probe(["FAIL_PREFLOOR"]))

    def run2(stage, argv, timeout=None, idempotent=False):
        if stage == "chain_clear_goal_mark":
            return 0, "KW_CHAIN_GOAL_MARK KEPT\n"
        return run(stage, argv, timeout=timeout, idempotent=idempotent)
    assert KW.private_chain(sp, res, out, "route", run2, fail, {}, popen=popen, wait=wait, sleep=lambda s: None) == 1
    assert res["stage"] == "chain_admit" and "FAIL_PREFLOOR" in res["tail"] and not popens
    # FAIL_POSTCTS (a real gate) is never touched
    sp, res, out, run, fail, popen, wait, calls, popens, waits, K = chain_fixture(tmp_path, monkeypatch, probe=_probe(["FAIL_POSTCTS"]))
    assert KW.private_chain(sp, res, out, "route", run, fail, {}, popen=popen, wait=wait, sleep=lambda s: None) == 1
    assert "chain_clear_goal_mark" not in [c[0] for c in calls]


def test_private_run_item_drives_from_rt_current(tmp_path):
    ctl = tmp_path / "rtcur" / "tools" / "autopilot"
    ctl.mkdir(parents=True)
    (ctl / "kit_wave.py").write_text("# rt/current driver\n")
    priv, wave = tmp_path / "p.json", tmp_path / "w.json"
    priv.write_text(json.dumps({"private": {"lane": "X"}}))
    wave.write_text(json.dumps({"die": "s81"}))
    own = Path(KW.__file__).resolve()
    env = {"OT_CONTROL_ROOT": str(ctl)}
    assert KW.runitem_driver(str(priv), env) == (ctl / "kit_wave.py").resolve()
    assert KW.runitem_driver(str(wave), env) == own
    assert KW.runitem_driver(str(priv), dict(env, KW_DRIVER_FROM="/old/kit_wave.py")) == own
    assert KW.runitem_driver(str(priv), {"OT_CONTROL_ROOT": "0"}) == own
