"""FLOW-FLEET-R2 F1 (CPU charged by measured class cores) and P1 (probe line): FABLE-FLOW-0800."""
import contextlib, importlib.machinery, importlib.util, io, os, pathlib
from unittest.mock import patch

P = str(pathlib.Path(__file__).with_name("ot-heavy-reconcile"))
loader = importlib.machinery.SourceFileLoader("ot_heavy_reconcile_cpu", P)
R = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_heavy_reconcile_cpu", loader))
loader.exec_module(R)


def test_cpu_interval_measures_cores_and_restarts_on_counter_drop():
    s = {}
    assert R.cpu_interval(s, 100.0, 0) is None                       # first sample: nothing to difference
    assert R.cpu_interval(s, 110.0, 5_000_000) is None               # < 30 s since the last sample: keep waiting
    assert abs(R.cpu_interval(s, 160.0, 120_000_000) - 2.0) < 1e-6   # 120 core-s over 60 s = 2 cores
    assert R.cpu_interval(s, 220.0, 1_000_000) is None               # a container ended: counter fell, interval restarts
    assert s["cpu_iv"] == [2.0]


def test_expected_cores_class_p90_else_share_of_declared_threads():
    h = {"route": [4.0, 6.0, 8.0, 30.0]}
    assert R.expected_cores("route", 16, h, 0.9, 3, 0.5) == 16.0     # p90 of 4 runs = index 3 -> 30, capped by the declared 16
    assert R.expected_cores("route", 16, {"route": [4.0, 6.0, 8.0]}, 0.5, 3, 0.5) == 6.0
    assert R.expected_cores("new", 16, h, 0.9, 3, 0.5) == 8.0        # no history: half the declared threads
    assert R.expected_cores("route", 16, {"route": [4.0]}, 0.9, 3, 0.5) == 8.0   # fewer than min_n runs: fallback


def test_cpu_charge_blocks_over_committed_busy_host_only():
    units = [("u%d" % i, 48, "route", 0) for i in range(10)]
    hist = {"route": [8.0, 8.0, 8.0]}
    th = lambda u: 16
    ok, why = R.cpu_charge_check("route", 16, units, hist, th, 96, 120.0)        # 80 committed + 8 <= 96 : fits
    assert ok and "CPU_CHARGE" in why
    ok, why = R.cpu_charge_check("route", 16, units + [("x", 48, "route", 0)] * 2, hist, th, 96, 120.0)
    assert not ok and "104" not in why and "> 96" in why                            # 96 + 8 > 96
    ok, why = R.cpu_charge_check("route", 16, units * 3, hist, th, 96, 40.0)         # same books, idle host (load 40 < 0.6 x 96): not charged
    assert ok and "not charged" in why


def test_cpu_history_reads_the_tsv(tmp_path):
    f = tmp_path / "cpu-peaks.tsv"
    f.write_text("t\tu1\troute\t6.5\t9\t300\nt\tu2\troute\t3.5\t4\t300\t1.2\nbad\n")
    assert R.cpu_history(str(f)) == {"route": [1.2, 2.6]}          # a 7-column row: its mean; an older 6-column row: 0.4 x its p90


def test_probe_line_small_threads_and_gb():
    with patch.dict(os.environ, {"SMALL_JOB_GB": "8", "OT_HEAVY_THREADS": "4"}):
        assert R.probe_like(32) and R.small_like(32) and not R.probe_like(48)
    with patch.dict(os.environ, {"SMALL_JOB_GB": "8", "OT_HEAVY_THREADS": "16"}):
        assert not R.probe_like(32) and R.small_like(6)              # a 16-thread 32 GB job is a kit
    with patch.dict(os.environ, {"SMALL_JOB_GB": "0", "OT_HEAVY_THREADS": "2"}):
        assert not R.probe_like(32)                                  # no small lane on this host


def test_gate_admits_a_32gb_probe_through_the_small_line_while_a_plan_job_waits():
    env = {"SIMPLE_ADMIT": "1", "SMALL_JOB_GB": "8", "OT_HEAVY_THREADS": "4", "INV_HEADROOM_GB": "128", "PLAN_PRIO": "0"}
    with patch.dict(os.environ, env), patch.object(R, "classify", return_value="probe:db"), patch.object(R, "sizes", return_value={}), \
            patch.object(R, "meminfo", return_value=(1000.0, 400.0)), patch.object(R, "running_units_light", return_value=[]), \
            patch.object(R.glob, "glob", return_value=[]):      # hermetic: no live res.* files of the host count as running small jobs
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            R.gate_locked(32, ["x"])
    assert out.getvalue().startswith("OK 32") and "SMALL_JOB lane" in out.getvalue()
