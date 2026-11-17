"""WAVE-FLOW-R2 11-17: ot_wait never reports RUNNING for an exited unit (KV: six dead ring masters 'RUNNING' for 85 minutes)."""
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ot_wait as W


def fake(props, pids_alive=(), log="", procs="", files=None):
    """a runner answering the commands ot_wait issues"""
    def run(host, cmd, timeout=60):
        if cmd.startswith("systemctl --user show"):
            return 0, "\n".join(f"{k}={v}" for k, v in props.items())
        if "/proc/" in cmd and "grep -q" in cmd:
            pid = int(cmd.split("/proc/")[1].split("/")[0].split(" ")[0])
            return 0, f"{pid}\n" if pid in pids_alive else ""
        if "cgroup.procs" in cmd:
            return 0, "\n".join(str(x) for x in pids_alive)
        if "journalctl" in cmd or cmd.startswith("tail -n") and "FAIL_" not in cmd:
            return 0, log
        if cmd.startswith("ps -eo"):
            return 0, procs
        if "ls -1 FAIL_*" in cmd:
            return (0, "\n".join(files or [])) if files else (1, "")
        if "tail -n 5 FAIL" in cmd:
            return 0, "reason: gate failed\n"
        if cmd.startswith("ls -1t"):
            return 0, ""
        return 0, ""
    return run


def props(act="active", sub="running", res="success", status="0", pid="4242", load="loaded"):
    return dict(LoadState=load, ActiveState=act, SubState=sub, Result=res, ExecMainStatus=status, MainPID=pid, ControlGroup="", Type="simple")


def test_live_unit_is_running_and_times_out():
    t = iter(range(0, 1000, 100))
    r = W.wait(unit="u", run=fake(props(), pids_alive=(4242,)), timeout=250, poll=1, sleep=lambda s: None, now=lambda: next(t))
    assert r["state"] == "TIMEOUT" and "live pids" in r["reason"]
    assert W.wait(unit="u", run=fake(props(), pids_alive=(4242,)), once=True)["state"] == "RUNNING"


def test_active_unit_with_no_live_process_is_never_running():
    """the KV incident: systemd still says active/running, the process is gone"""
    r = W.wait(unit="u", run=fake(props(pid="4242", status="0"), pids_alive=(), log="x\nlast line\n"), once=True)
    assert r["state"] in ("DONE", "FAILED") and r["state"] != "RUNNING" and "no live process" in r["reason"]
    r = W.wait(unit="u", run=fake(props(pid="0", status="137"), pids_alive=(), log="killed\n"), once=True)
    assert r["state"] == "FAILED" and r["rc"] == 137 and r["log_tail"] == ["killed"]


def test_exit_statuses():
    r = W.wait(unit="u", run=fake(props("failed", "failed", "exit-code", "3", "0"), log="boom\n"), once=True)
    assert r["state"] == "FAILED" and r["rc"] == 3 and r["log_tail"] == ["boom"]
    assert W.wait(unit="u", run=fake(props("inactive", "dead", "success", "0", "0")), once=True)["state"] == "DONE"
    assert W.wait(unit="u", run=fake(props("inactive", "dead", "success", "7", "0")), once=True)["state"] == "FAILED"


def test_collected_unit_uses_the_client_log_or_fails():
    gone = props(load="not-found", act="inactive", sub="dead", pid="0")
    ok = W.wait(unit="u", run=fake(gone, log="ot-run: RAN on epyc2 (unit oth-u-1): exit 0\n"), once=True)
    assert ok["state"] == "DONE" and ok["rc"] == 0
    bad = W.wait(unit="u", run=fake(gone, log="ot-run: RAN on epyc2 (unit oth-u-1): exit 9\n"), once=True)
    assert bad["state"] == "FAILED" and bad["rc"] == 9
    none = W.wait(unit="u", run=fake(gone, log="nothing\n"), once=True)
    assert none["state"] == "FAILED" and "no exit status" in none["reason"]
    nr = W.wait(unit="u", run=fake(props("inactive", "dead", "success", "0", "0"), log="ot-run: NOT RUN on x: no host\n"), once=True)
    assert nr["state"] == "FAILED"


def test_kit_mode():
    assert W.wait(kit="/k", run=fake({}, procs="123\n"), once=True)["state"] == "RUNNING"
    r = W.wait(kit="/k", run=fake({}, files=["FAIL_POSTCTS"]), once=True)
    assert r["state"] == "FAILED" and "FAIL_POSTCTS" in r["reason"] and r["log_tail"] == ["reason: gate failed"]
    assert W.wait(kit="/k", run=fake({}), once=True)["state"] in ("DONE", "FAILED")


def test_real_systemd_unit_exit_status():
    """a real transient user unit (skipped where systemd --user is unavailable)"""
    name = "otw-test-" + uuid.uuid4().hex[:8]
    r = subprocess.run(["systemd-run", "--user", f"--unit={name}", "--collect", "--property=RemainAfterExit=no", "bash", "-c", "echo hello; exit 3"],
                       capture_output=True, text=True)
    if r.returncode:
        import pytest
        pytest.skip("no systemd --user")
    res = W.wait(unit=name + ".service", timeout=30, poll=1)
    assert res["state"] in ("FAILED", "DONE") and res["state"] != "RUNNING"


def test_a_failed_scope_with_result_success_takes_its_exit_status_from_the_client_log():
    import ot_wait as W
    props = {"Id": "oth-ubuntu-1-2.scope", "LoadState": "loaded", "ActiveState": "failed", "SubState": "failed", "Result": "success", "ExecMainStatus": "0"}
    ok = W.classify_unit(props, [], ["ot-run: RAN on epyc8 (unit oth-ubuntu-1-2): exit 0"])
    assert ok[0] == "DONE" and ok[1] == 0
    bad = W.classify_unit(props, [], ["ot-run: RAN on epyc8 (unit oth-ubuntu-1-2): exit 3"])
    assert bad[0] == "FAILED" and bad[1] == 3
    none = W.classify_unit(props, [], [])
    assert none[0] == "FAILED" and "no exit status" in none[2]                                  # nothing recorded: still FAILED, never DONE by guess


def test_a_service_failure_and_a_non_success_scope_result_stay_failed():
    import ot_wait as W
    svc = {"Id": "x.service", "LoadState": "loaded", "ActiveState": "failed", "SubState": "failed", "Result": "exit-code", "ExecMainStatus": "1"}
    assert W.classify_unit(svc, [], ["ot-run: RAN on h (unit x): exit 0"])[0] == "FAILED"
    oom = {"Id": "oth-a.scope", "LoadState": "loaded", "ActiveState": "failed", "SubState": "failed", "Result": "oom-kill"}
    assert W.classify_unit(oom, [], ["ot-run: RAN on h (unit x): exit 0"])[0] == "FAILED"
