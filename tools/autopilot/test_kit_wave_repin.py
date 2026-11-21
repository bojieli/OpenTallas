"""REPIN-1121: a single-host-pinned stage not admitted within repin_s moves to a host that admits it; admitted or unpinned stages are never touched."""
import os, sys, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import kit_wave_roam as R

STATUS = "ot-run status: epyc2 admits 0 GB (avail 107) | intel1 admits 0 GB | epyc7 admits 58 GB (x) | epyc9 admits 129 GB (y) | next 16-thread"


def test_parse_and_pick():
    a = R.parse_admits(STATUS)
    assert a == {"epyc2": 0, "intel1": 0, "epyc7": 58, "epyc9": 129}
    assert R.pick_alt(a, 24, {"epyc2"}, ["epyc7", "epyc9", "epyc2"]) == "epyc9"
    assert R.pick_alt(a, 200, {"epyc2"}, ["epyc7", "epyc9"]) == ""
    assert R.single_pin(["ot-run", "--hosts", "epyc2"]) == "epyc2" and R.single_pin(["x", "--hosts", "a,b"]) == "" and R.single_pin(["x"]) == ""


class FakeP:
    def __init__(self, argv, waits):
        self.argv, self.waits, self.returncode, self.term = argv, waits, None, False

    def communicate(self, timeout=None):
        if self.term:
            self.returncode = -15
            return "", None
        if self.waits > 0 and timeout is not None:
            self.waits -= 1
            raise subprocess.TimeoutExpired("x", timeout)
        self.returncode = 0
        return "done " + " ".join(self.argv), None

    def terminate(self):
        self.term = True

    def kill(self):
        self.term = True


class Ops:
    def __init__(self, rc=0):
        self.calls, self.rc = [], rc

    def copy(self, s, d, p, delete=True):
        self.calls.append((s, d, p, delete))
        return self.rc, ""


def go(tmp, live_text, rc=0, waits=100, others=("epyc7", "epyc9"), status=STATUS):
    live = tmp / "geom.live.log"
    live.write_text(live_text)
    procs, t = [], [0.0]

    def popen(argv, **k):
        pr = FakeP(argv, waits if not procs else 0)
        procs.append(pr)
        return pr

    def clock():
        t[0] += 700
        return t[0]
    logs, ops = [], Ops(rc)
    argv = ["ot-run", "--mem", "24", "--dir", "/w/a/attempt_3", "--hosts", "epyc2", "--", "bash"]
    d = R.run_watch(argv, None, str(live), list(others), "/w/a/attempt_3", ops, lambda: status, logs.append, repin_s=1800, poll_s=1, clock=clock, popen=popen)
    return d, procs, ops, logs


def test_unadmitted_pinned_stage_moves(tmp_path):
    d, procs, ops, logs = go(tmp_path, "ot-heavy: waiting")
    assert d.returncode == 0 and "--hosts epyc9" in " ".join(procs[-1].argv) and procs[0].term
    assert ops.calls == [("epyc2", "epyc9", "/w/a/attempt_3", True), ("epyc9", "epyc2", "/w/a/attempt_3", False)]
    assert any("KW_REPIN" in x and "ran on epyc9" in x for x in logs)


def test_admitted_stage_is_never_touched(tmp_path):
    d, procs, ops, logs = go(tmp_path, "ot-heavy: admitted on epyc2", waits=3)
    assert len(procs) == 1 and not procs[0].term and ops.calls == []


def test_copy_failure_or_no_free_host_keeps_the_pin(tmp_path):
    d, procs, ops, logs = go(tmp_path, "waiting", rc=1, waits=6)
    assert len(procs) == 1 and not procs[0].term and any("copy to" in x for x in logs)
    d, procs, ops, logs = go(tmp_path, "waiting", waits=6, status="ot-run status: epyc2 admits 0 GB | epyc7 admits 3 GB")
    assert len(procs) == 1 and ops.calls == []


def test_no_roam_hosts_or_outside_attempt_dir(tmp_path):
    d, procs, ops, logs = go(tmp_path, "waiting", waits=6, others=())
    assert len(procs) == 1 and ops.calls == []
