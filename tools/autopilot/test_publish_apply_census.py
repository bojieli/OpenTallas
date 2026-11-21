"""ADOPT-CENSUS-1800: the apply passes the previous event to the background precheck unit (EVENT-CENSUS) and the tools pin (ADOPT-DIFF)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_apply as PA  # noqa: E402


def test_prev_event_of_live_config():
    live = {"plan": "/t0/physical/die_plan/s81/p.json", "src": "/t0", "event": "J5", "work_root": "/w/runs/s81/kit-wave"}
    p = PA.prev_event_of(live, "s81")
    assert p == {"plan": "/t0/physical/die_plan/s81/p.json", "src": "/t0", "event": "J5", "kit_root": "/w/runs/s81/kit-wave/s81/J5/items"}
    assert PA.prev_event_of({}, "s81") == {}


def test_precheck_argv_carries_census_args():
    obj = {"marker": {"die": "s81", "tree": "/t1", "plan": "physical/die_plan/s81/p.json", "hosts": ["epyc8"]}}
    res = {"event": "J6", "applied": "s81", "gen_hosts": ["epyc8"]}
    prev = PA.prev_event_of({"plan": "/t0/physical/die_plan/s81/p.json", "src": "/t0", "event": "J5", "work_root": "/w"}, "s81")
    pa = PA.precheck_argv(obj, res, "S81-J6-ASSEMBLY", now=5, prev=prev, tools_sha="abc123")
    s = " ".join(pa)
    assert "--prev-plan /t0/physical/die_plan/s81/p.json" in s and "--prev-event J5" in s
    assert "--prev-tools /t0/tools/die_plan" in s and "--prev-kits /w/s81/J5/items" in s and "--tools-sha abc123" in s
    # same plan (a re-apply) runs no census; no previous event: precheck as before
    same = PA.precheck_argv(obj, res, "L", now=5, prev={"plan": "/t1/physical/die_plan/s81/p.json"})
    assert "--prev-plan" not in same
    assert "--prev-plan" not in PA.precheck_argv(obj, res, "L", now=5)
