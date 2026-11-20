"""STARTCANARY-1400: a host whose container start has not succeeded for 10 min reports admit 0."""
import importlib.machinery, importlib.util, json, pathlib, tempfile

P = str(pathlib.Path(__file__).with_name("ot-heavy-reconcile"))
loader = importlib.machinery.SourceFileLoader("recon_canary", P)
M = importlib.util.module_from_spec(importlib.util.spec_from_loader("recon_canary", loader))
loader.exec_module(M)
FREE = json.dumps({"admit_gb": 150, "die_admit_gb": 150, "free_gb": 150, "waiting_gb": 0})


def fake(rc_run):
    def run(*a, t=None):
        if a[0] == "images":
            return 0, "opentallas/orfs:asap7lock-grtoff\n"
        return rc_run, ""
    return run


def test_green_canary_keeps_the_admit():
    with tempfile.TemporaryDirectory() as d:
        r = M.start_canary(d, now=1000.0, run=fake(0))
        assert r["ok"] and r["last_ok"] == 1000.0
        assert M.apply_canary(FREE, d, now=1300.0) == FREE


def test_no_start_for_ten_minutes_admits_zero():
    with tempfile.TemporaryDirectory() as d:
        M.start_canary(d, now=1000.0, run=fake(0))
        M.start_canary(d, now=1300.0, run=fake(124))               # one timed-out probe: still inside the 10 min
        assert json.loads(M.apply_canary(FREE, d, now=1400.0))["admit_gb"] == 150
        M.start_canary(d, now=1600.0, run=fake(124))
        o = json.loads(M.apply_canary(FREE, d, now=1700.0))        # 700 s since the last success
        assert o["admit_gb"] == 0 and o["die_admit_gb"] == 0 and "no container start" in o["canary"]


def test_no_record_or_no_image_is_no_gate():
    with tempfile.TemporaryDirectory() as d:
        assert M.apply_canary(FREE, d, now=5000.0) == FREE
        assert M.start_canary(d, run=lambda *a, t=None: (0, "")) is None
        assert M.apply_canary(FREE, d, now=5000.0) == FREE
