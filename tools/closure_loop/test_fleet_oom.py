"""FLEET-OOM (2026-10-18): the stage runner records the stage's RSS peak and the OOM kills of its processes; an OOM kill
is a flow failure (retry once), never NEEDS_RTL; repeats of a block + stage admit at the measured peak."""
import json, os, subprocess, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import closure_loop as cl


def run_runner(tmp, body, decl=0):
    d = Path(tmp) / "run" / "cl"
    d.mkdir(parents=True)
    (d / "SRC_DIR").write_text(tmp)
    (d / "run.sh").write_text(cl.RUNNER)
    (d / "t1.sh").write_text(body)
    (d / "t1.decl").write_text(f"{decl}\n")
    subprocess.run(["setsid", "bash", str(d / "run.sh"), "t1"], timeout=120, check=True)
    return d


def test_runner_rc_peak_and_no_false_kill():
    with tempfile.TemporaryDirectory() as tmp:
        d = run_runner(tmp, "python3 -c 'import time; b = bytearray(64 << 20); time.sleep(20)'\nexit 3\n")
        assert (d / "t1.rc").read_text().strip() == "3"
        assert int((d / "t1.peak_kb").read_text()) > 60000          # the 64 MiB python was sampled
        assert not (d / "t1.oomkill").exists()                      # nothing on this host killed one of its pids


def test_learned_ram(tmp_path=None):
    tmp = Path(tempfile.mkdtemp())
    old = cl.STAGE_PEAKS
    try:
        cl.STAGE_PEAKS = tmp / "stage_peaks.json"
        cl._peaks_cache[:] = [None, {}]
        assert cl.learned_ram("blk", "bench_x", 160) == 160
        j = dict(name="j1", host="h", spec=dict(block="blk"), events=[])
        cl.record_stage_peak(j, dict(key="bench_x", ram=160), 298 * 1048576)
        assert json.loads(cl.STAGE_PEAKS.read_text())["blk|bench_x"]["peak_gb"] == 298.0
        assert cl.learned_ram("blk", "bench_x", 160) == 343            # ceil(1.15 x 298)
        assert cl.learned_ram("blk", "bench_x", 400) == 400            # never below the declaration
        assert cl.learned_ram("other", "bench_x", 160) == 160
        spec = dict(block="blk", stages=dict(bench=[dict(name="x", cmd="true", expect="pass", peak_ram_gb=160)]))
        b = cl.stage_list(spec)[0]
        assert b["ram"] == 343 and b["declared_ram"] == 160
    finally:
        cl.STAGE_PEAKS = old
        cl._peaks_cache[:] = [None, {}]


def test_oom_retry_is_flow_failure():
    j = dict(name="j", host="h", attempt=1, retries_used=0, status="RUNNING", spec={}, events=[])
    cl.oom_retry(j, dict(key="bench_eq_mut1"), None, 'Oct 18 07:37:39 h earlyoom[1]: sending SIGTERM to process 5 uid 1000 "vvp"')
    assert j["status"] == "READY" and j["attempt"] == 2 and j["crashes"][0]["cls"] == "oom_kill"


if __name__ == "__main__":
    test_runner_rc_peak_and_no_false_kill(); test_learned_ram(); test_oom_retry_is_flow_failure()
    print("test_fleet_oom PASS")
