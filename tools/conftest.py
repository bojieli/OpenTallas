"""tools/ pytest preconditions (PROFILE-1 2026-11-13).

The sign-off profile switch OT_SIGNOFF_PROFILE defaults to 'minimal' (R-MINIMAL, OWNER 11-13: only DRC 0, TT setup,
internal FF hold and bind/latency block).  The suites written before it assert the legacy gates (preflight, visual,
LEC, path gate, io_hold_parent, ...), so every test runs with the legacy profile unless it sets or deletes the variable
itself; tools/die_plan/test_signoff_profile.py covers the minimal profile and its legacy fallback."""
import os
import pytest

# TOOLS-CONVERGE-1115: the kit_wave launch gate (autopilot/tool_skew.py) never ssh-es to a die tree host under test
os.environ.setdefault("OT_TOOL_SKEW_REMOTE", "0")

# OWNER 11-20 #6: generators default to a 300-um placed-hop cap (cbc_rules.REACH_UM_PER_HOP).  The geometry fixtures of the
# suites before it are drawn at the 405 rule; they keep running there.  test_cbc_rules_default.py checks the 300 default.
os.environ.setdefault("OT_CBC_REACH_UM", "405")


@pytest.fixture(autouse=True)
def _legacy_signoff_profile_default(monkeypatch):
    monkeypatch.setenv("OT_SIGNOFF_PROFILE", "legacy")


# FLOW-HEALTH-1 11-15 (FABLE-FLOW-1600): `lec_async.sh start` leaves a detached `lec_async.sh watch <kit>` (setsid nohup, ppid 1) behind.
# 15 of them sat on intel2 and 16 on epyc8 from test_missing_proof_reference and the spill handoff tests, which fed the 2400 s gate timeouts.
# Every watcher a test starts carries this session's marker in its environment (set below); after each test the fixture kills them by exact
# PID (cmdline re-checked) and asserts none is left.  Watchers of other pytest sessions and of real kits never carry the marker.
import signal
import time

_SESSION = f"pytest-{os.getpid()}"
os.environ["OT_TEST_WATCH_SESSION"] = _SESSION


def session_lec_watchers(session=_SESSION):
    """pids of `lec_async.sh watch` processes started under this pytest session"""
    out = []
    for name in os.listdir("/proc"):
        if not name.isdigit() or int(name) == os.getpid():
            continue
        try:
            cmd = open(f"/proc/{name}/cmdline", "rb").read().replace(b"\0", b" ").decode("utf-8", "replace")
            if "lec_async.sh watch" not in cmd:
                continue
            env = open(f"/proc/{name}/environ", "rb").read()
        except OSError:
            continue
        if f"OT_TEST_WATCH_SESSION={session}".encode() in env.split(b"\0"):
            out.append(int(name))
    return out


def reap_lec_watchers(session=_SESSION, wait_s=5.0):
    """SIGTERM then SIGKILL every watcher of the session; -> the pids still alive afterwards"""
    t0 = time.time()
    sig = signal.SIGTERM
    while True:
        pids = session_lec_watchers(session)
        if not pids:
            return []
        for p in pids:
            try:
                os.kill(p, sig)
            except OSError:
                pass
        if time.time() - t0 > wait_s / 2:
            sig = signal.SIGKILL
        if time.time() - t0 > wait_s:
            return session_lec_watchers(session)
        time.sleep(0.1)


@pytest.fixture(autouse=True)
def _reap_lec_watchers():
    yield
    left = reap_lec_watchers()
    assert not left, f"lec_async.sh watch process(es) left behind by this test: {left}"


import pytest


@pytest.fixture(autouse=True)
def _fixed_hub_disk(monkeypatch):
    """WAVE-FLOW-R 11-17 (FABLE-FLOW-0500 item 1): the wave tests read a fixed hub disk (500 GB free), never the live hub, so a hub under its floor cannot fail
    the rt smoke tests (9 syncs in a row failed 01:51-02:31).  A test that needs another value passes statvfs= explicitly."""
    try:
        import types
        import kit_wave
    except Exception:
        return
    monkeypatch.setattr(kit_wave, "_HUB_STATVFS", lambda p: types.SimpleNamespace(f_bavail=500, f_frsize=2**30), raising=False)
