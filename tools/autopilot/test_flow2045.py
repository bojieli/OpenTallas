"""FLOW-FIX-2045 (FABLE-FLOW-1949 classes 3-6): relabelled event keeps its repeat counters, cancelled scopes are reaped, host choice by room, alerts once per hour per key"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as KW  # noqa: E402


def _cfg(event, src="S1"):
    return {"dies": {"s81": {"event": event, "gen_host": "h", "plan": "/p.json", "src_sha": src}}}


def _st(event, block="B" * 40, src="S1"):
    return {"plans": {f"h:/p.json|{event}": {"blocks": {"t1": block}}},
            "fail_keys": {"s81|t1": {"key": "k", "event": "b4bb6a8b1e9", "parts": {"block": block, "src": src}, "n": 2}},
            "fail_sigs": {"s81|t1": {"attempts": ["b4bb6a8b1e9@3", "b4bb6a8b1e9@4"], "n": 2}}}


def test_relabel_of_an_unchanged_plan_keeps_repeat_counters():
    st = _st("b05c98f7919")
    assert KW.prune_stale_fail_entries(_cfg("b05c98f7919"), st) == (0, 0)
    assert "s81|t1" in st["fail_keys"] and "s81|t1" in st["fail_sigs"]


def test_a_changed_block_or_src_still_drops_the_old_event_entry():
    st = _st("b05c98f7919", block="C" * 40)                       # the plan block changed
    st["fail_keys"]["s81|t1"]["parts"]["block"] = "B" * 40
    assert KW.prune_stale_fail_entries(_cfg("b05c98f7919"), st) == (1, 1)
    st = _st("b05c98f7919")
    assert KW.prune_stale_fail_entries(_cfg("b05c98f7919", src="S2"), st) == (1, 1)      # the src tree changed


def test_breaker_inputs_ignore_the_event_label():
    a = KW.breaker_inputs({"dies": {"s81": {"event": "e1", "plan_sha": "P", "src_sha": "S"}}}, "s81")
    b = KW.breaker_inputs({"dies": {"s81": {"event": "e2", "plan_sha": "P", "src_sha": "S"}}}, "s81")
    c = KW.breaker_inputs({"dies": {"s81": {"event": "e2", "plan_sha": "P2", "src_sha": "S"}}}, "s81")
    assert a == b and a != c


def _hosts(**over):
    base = {"epyc8": {"admit": 40, "load": 290, "cores": 96, "wait_gb": 907}, "intel1": {"admit": 400, "load": 60, "cores": 112, "wait_gb": 0},
            "epyc9": {"admit": 250, "load": 40, "cores": 96, "wait_gb": 0}}
    base.update(over)
    return {"load_hold": False, "host_share": {"epyc8": 2.0, "intel1": 2.0},
            "dies": {"s81": {"gen_host": "epyc8", "gen_hosts": ["epyc8", "epyc9", "intel1"], "event": "e", "plan": "/p", "src": "/s"}},
            "_hub": "intel2", "_otrun_status": {h: dict(v) for h, v in base.items()}}


def test_no_hold_mode_still_orders_the_pick_by_load_not_by_memory_alone():
    """FLOW-FIX-2045 class 3: load_hold false made the pick a memory score x host_share; epyc8 (load 290/96, 907 GB waiting, share 2.0) kept the burst"""
    c = _hosts()
    picks = [KW.pick_gen_host(c, "s81", take=72, threads=16) for _ in range(12)]
    assert "epyc8" not in picks, picks
    assert set(picks) == {"intel1", "epyc9"}
    assert KW.load_hold(_hosts(), "s81") == ""                                   # still no hold: nothing is refused


def test_burst_spreads_across_hosts_by_cores_when_memory_is_exhausted():
    c = _hosts(intel1={"admit": 0, "load": 60, "cores": 112, "wait_gb": 0}, epyc9={"admit": 0, "load": 40, "cores": 96, "wait_gb": 0})
    picks = [KW.pick_gen_host(c, "s81", take=72, threads=16) for _ in range(20)]
    assert "epyc8" not in picks and {"intel1", "epyc9"} <= set(picks), picks
    n9, n1 = picks.count("epyc9"), picks.count("intel1")
    assert abs(n9 - n1) <= 6                                                        # each pick adds its threads to the host load: the two share the burst


class _AP:
    def __init__(self):
        self.lines = []

    def log(self, m):
        self.lines.append(m)


def test_log_hourly_once_per_key_per_hour_and_counts_what_it_held_back():
    ap, st = _AP(), {}
    assert KW.log_hourly(ap, st, "REPEAT|s81|t1", "a", now=1000.0)
    assert not KW.log_hourly(ap, st, "REPEAT|s81|t1", "a", now=1700.0) and not KW.log_hourly(ap, st, "REPEAT|s81|t1", "a", now=2400.0)
    assert KW.log_hourly(ap, st, "REPEAT|s81|t2", "b", now=2400.0)                         # another key is its own line
    assert KW.log_hourly(ap, st, "REPEAT|s81|t1", "a", now=1000.0 + KW.LOG_HOURLY_S)
    assert ap.lines == ["a", "b", "a [+2 identical line(s) in the last hour]"]


def test_adopt_guard_pretick_alert_is_rate_limited_in_the_script():
    import pathlib
    t = (pathlib.Path(__file__).with_name("adopt_guard_pretick.sh")).read_text()
    assert ".adopt_alert_seen" in t and "-mmin -60" in t
    assert KW.log_hourly.__doc__.count("hour") >= 2


def test_stop_kit_reaps_a_container_less_scope_under_a_cancelled_root_and_verifies(tmp_path):
    """FLOW-FIX-2045 class 5: an oth-* scope with no container, whose process lives under the cancelled attempt's root, is stopped by the same pass and reported gone"""
    import json
    import shutil
    import subprocess
    import time
    import wave_jobs as WJ
    if not (shutil.which("systemd-run") and shutil.which("docker")):
        import pytest
        pytest.skip("systemd-run / docker not available")
    env = dict(os.environ, XDG_RUNTIME_DIR=os.environ.get("XDG_RUNTIME_DIR") or "/run/user/%d" % os.getuid())
    root = tmp_path / "kit-wave" / "s81" / "e" / "items" / "t1" / "attempt_2"
    other = tmp_path / "kit-wave" / "s81" / "e" / "items" / "t1" / "attempt_3"
    root.mkdir(parents=True); other.mkdir(parents=True)
    unit = "oth-flowfix2045-%d" % int(time.time())
    unit2 = "oth-flowfix2045b-%d" % int(time.time())
    for u, d in ((unit, root), (unit2, other)):
        r = subprocess.run(["systemd-run", "--user", "--scope", "--quiet", "--unit", u, "bash", "-c", "cd %s && exec sleep 300" % d], env=env, capture_output=True, timeout=30) if False else None
        subprocess.Popen(["systemd-run", "--user", "--scope", "--quiet", "--unit", u, "bash", "-c", "cd %s && exec sleep 300" % d], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    try:
        if subprocess.run(["systemctl", "--user", "is-active", "--quiet", unit + ".scope"], env=env).returncode != 0:
            import pytest
            pytest.skip("user scope could not be started here")
        dry = subprocess.run(["python3", "-I", "-", json.dumps({"roots": [str(root)], "dry": True})], input=WJ.STOP_KIT, capture_output=True, text=True, env=env, timeout=120)
        assert unit + ".scope" in json.loads(dry.stdout.strip().splitlines()[-1])["scopes"]
        assert subprocess.run(["systemctl", "--user", "is-active", "--quiet", unit + ".scope"], env=env).returncode == 0      # dry stops nothing
        real = subprocess.run(["python3", "-I", "-", json.dumps({"roots": [str(root)]})], input=WJ.STOP_KIT, capture_output=True, text=True, env=env, timeout=120)
        out = json.loads(real.stdout.strip().splitlines()[-1])
        assert unit + ".scope" in out["scopes"] and unit2 + ".scope" not in out["scopes"] and not out.get("left")
        assert subprocess.run(["systemctl", "--user", "is-active", "--quiet", unit + ".scope"], env=env).returncode != 0
        assert subprocess.run(["systemctl", "--user", "is-active", "--quiet", unit2 + ".scope"], env=env).returncode == 0     # the next attempt's scope (a sibling dir) is untouched
    finally:
        for u in (unit + ".scope", unit2 + ".scope"):
            subprocess.run(["systemctl", "--user", "stop", u], env=env, capture_output=True)
