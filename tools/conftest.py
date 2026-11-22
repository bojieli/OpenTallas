"""tools/ pytest preconditions (PROFILE-1 2026-11-13).

The sign-off profile switch OT_SIGNOFF_PROFILE defaults to 'minimal' (R-MINIMAL, OWNER 11-13: only DRC 0, TT setup,
internal FF hold and bind/latency block).  The suites written before it assert the legacy gates (preflight, visual,
LEC, path gate, io_hold_parent, ...), so every test runs with the legacy profile unless it sets or deletes the variable
itself; tools/die_plan/test_signoff_profile.py covers the minimal profile and its legacy fallback."""
import os
import pytest

# FLEET-GUARD-1122 (FABLE-FLOW-0600 E1; incident BIND-DOOM-STORM 11-22: merge-queue autopilot tests ran bind_doom.step for real -> 64 sweeps, 189 remote
# scans, epyc9 load 197).  ONE harness-level guard instead of a per-feature one: under pytest every subprocess start whose program (after timeout / nice /
# env / setsid / nohup / ionice / stdbuf wrappers) is a real fleet tool -- ssh, scp, systemd-run, ot-run, ot-heavy, ot-delete, ot-push-main -- runs
# a stub that fails like an unreachable host (rc 255; OT_TEST_FLEET_STRICT=1 raises FleetUnderTest instead).  Allowed: a program that resolves (via the call's PATH) to a file under the temp dir / --basetemp (a fake) or inside this checkout
# (the tool under test, e.g. tools/fleet/ot-run with its hermetic test env); installed copies (~/.local/bin, rt/current, /usr) are refused.  A test that really needs the real tool sets OT_TEST_FLEET_OK=1 (monkeypatch.setenv).  OT_UNDER_TEST=1 is exported for child shells.
import shutil
import sys
import subprocess
import tempfile

os.environ["OT_UNDER_TEST"] = "1"
FLEET_TOOLS = {"ssh", "scp", "systemd-run", "ot-run", "ot-heavy", "ot-delete", "ot-push-main"}
_WRAP = {"timeout", "nice", "env", "setsid", "nohup", "ionice", "stdbuf", "chrt", "taskset"}


class FleetUnderTest(RuntimeError):
    pass


def _program(argv):
    """the program a wrapped argv really runs (timeout 60 nice -n 10 ssh h ... -> ssh)"""
    i = 0
    while i < len(argv):
        w = os.path.basename(str(argv[i]))
        if w not in _WRAP:
            return str(argv[i])
        i += 1
        first = True
        while i < len(argv):
            x = str(argv[i])
            if x.startswith("-") or "=" in x and w == "env":
                if w in ("nice", "ionice", "taskset", "chrt") and x in ("-n", "-c", "-p") and i + 1 < len(argv):
                    i += 1
                i += 1
                continue
            if w in ("timeout", "taskset", "chrt") and first and (x[:1].isdigit() or w != "timeout"):
                first = False
                i += 1
                continue
            break
    return ""


_FAKE_ROOTS = {os.path.realpath(tempfile.gettempdir()), "/tmp", "/var/tmp",
               os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))}   # this checkout: its own scripts are the code under test


def pytest_configure(config):
    bt = getattr(config.option, "basetemp", None)
    if bt:
        _FAKE_ROOTS.add(os.path.realpath(str(bt)))


def _is_fake(path):
    rp = os.path.realpath(path)
    return any(rp.startswith(r.rstrip("/") + "/") for r in _FAKE_ROOTS)


def fleet_refusal(args, executable=None, shell=False, env=None):
    """-> '' or why this subprocess start would reach the real fleet"""
    if os.environ.get("OT_TEST_FLEET_OK") == "1" or (env or {}).get("OT_TEST_FLEET_OK") == "1":
        return ""
    if isinstance(args, (str, bytes)):
        argv = (args.decode() if isinstance(args, bytes) else args).split() if shell or isinstance(args, str) else [args]
    else:
        argv = [os.fspath(x) if not isinstance(x, (str, bytes)) else (x.decode() if isinstance(x, bytes) else x) for x in args]
    prog = executable or _program(argv)
    if not prog or os.path.basename(prog) not in FLEET_TOOLS:
        return ""
    path = prog if "/" in prog else shutil.which(prog, path=(env or os.environ).get("PATH"))
    if not path or not os.path.exists(path) or _is_fake(path):
        return ""
    return f"test started the real fleet tool {path}: {' '.join(argv)[:200]} (fake it, or OT_TEST_FLEET_OK=1)"


_popen_init = subprocess.Popen.__init__


FLEET_STUBBED = []
_STUB_RC = 255                          # what ssh returns for an unreachable host: code under test takes its "probe failed" path


def _guarded_init(self, args, *a, **k):
    why = fleet_refusal(args, k.get("executable"), k.get("shell", False), k.get("env"))
    if why:
        if os.environ.get("OT_TEST_FLEET_STRICT") == "1":
            raise FleetUnderTest(why)
        FLEET_STUBBED.append(why)       # the real tool never runs: a stub that fails like an unreachable host takes its place
        k["shell"], k["executable"] = False, None
        args = ["/bin/sh", "-c", 'echo "FleetUnderTest: $1" >&2; exit %d' % _STUB_RC, "fleet-guard", why[:300]]
    return _popen_init(self, args, *a, **k)


def pytest_terminal_summary(terminalreporter):
    if FLEET_STUBBED:
        terminalreporter.write_line(f"FLEET-GUARD-1122: {len(FLEET_STUBBED)} real fleet tool start(s) replaced by a failing stub in this process "
                                    f"(OT_TEST_FLEET_STRICT=1 raises): {FLEET_STUBBED[0][:160]}")


if not getattr(subprocess.Popen.__init__, "_ot_fleet_guard", False):
    _guarded_init._ot_fleet_guard = True
    subprocess.Popen.__init__ = _guarded_init
    subprocess._ot_fleet_guard_module = sys.modules.get(__name__)   # tests reach the guard helpers through here (conftest module names vary)

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
