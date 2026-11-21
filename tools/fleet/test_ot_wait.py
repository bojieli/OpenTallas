"""WAITER-STD-1600: ot_status records, ot-wait, and the ot-run / ot-push-main hooks."""
import json
import os
import subprocess
import sys
import time
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import ot_status as S  # noqa: E402

WAIT = str(HERE / "ot-wait")


def env(tmp, **kw):
    e = dict(os.environ, OT_STATUS_DIR=str(tmp), OT_STATUS_POST="0")
    e.pop("OT_LANE", None)
    e.update(kw)
    return e


def wait(tmp, *args, **kw):
    return subprocess.run([sys.executable, "-I", WAIT, *args], capture_output=True, text=True, env=env(tmp, **kw), timeout=60)


def rec_file(tmp, name, **kw):
    r = dict(schema=S.SCHEMA, kind="run", name=name, unit="", host=S.host(), pid=0, pid_start=None, lane="L", cmd="x", log="/l",
             t_start=1, state="done", rc=0, t_end=2)
    r.update(kw)
    (Path(tmp) / (name + ".json")).write_text(json.dumps(r))
    return r


def test_done_rc_is_the_exit_status(tmp_path):
    rec_file(tmp_path, "otrun-h-1", rc=3, unit="oth-abc")
    p = wait(tmp_path, "otrun-h-1")
    assert p.returncode == 3 and p.stdout.startswith("DIED rc=3 unit=oth-abc")
    p = wait(tmp_path, "oth-abc")                     # by unit name
    assert p.returncode == 3
    rec_file(tmp_path, "otrun-h-2", rc=0)
    p = wait(tmp_path, "otrun-h-2")
    assert p.returncode == 0 and p.stdout.startswith("DONE rc=0")


def test_unknown_target_is_never_success(tmp_path):
    assert wait(tmp_path, "otrun-nope-1").returncode == 66
    assert wait(tmp_path, "oth-nope").returncode == 66
    assert wait(tmp_path, "999999999").returncode == 66


def test_client_killed_without_status_is_died_71(tmp_path):
    c = subprocess.Popen(["sleep", "60"])
    rec_file(tmp_path, "otrun-h-9", pid=c.pid, pid_start=S.pid_start(c.pid), state="running", rc=None, t_end=None)
    c.kill(); c.wait()
    p = wait(tmp_path, "otrun-h-9", "--poll", "0.2")
    assert p.returncode == 71 and "DIED" in p.stdout and "killed" in p.stdout


def test_running_then_done(tmp_path):
    c = subprocess.Popen(["sleep", "60"])
    try:
        rec_file(tmp_path, "otrun-h-8", pid=c.pid, pid_start=S.pid_start(c.pid), state="running", rc=None, t_end=None)
        assert wait(tmp_path, "otrun-h-8", "--timeout", "1", "--poll", "0.2").returncode == 124
        rec_file(tmp_path, "otrun-h-8", pid=c.pid, pid_start=S.pid_start(c.pid), rc=5)
        assert wait(tmp_path, "otrun-h-8").returncode == 5
    finally:
        c.kill(); c.wait()


def test_exact_pid_wait_and_cmdline_guard(tmp_path):
    c = subprocess.Popen(["sleep", "2"])
    assert wait(tmp_path, str(c.pid), "--cmdline", "not-this").returncode == 2
    t0 = time.time()
    p = wait(tmp_path, str(c.pid), "--cmdline", "sleep", "--poll", "0.2")
    c.wait()
    assert p.returncode == 70 and p.stdout.startswith("ENDED rc=unknown") and time.time() - t0 < 30


def test_numeric_target_uses_client_record(tmp_path):
    c = subprocess.Popen(["sleep", "30"])
    try:
        rec_file(tmp_path, f"otrun-{S.host()}-{c.pid}", pid=c.pid, pid_start=S.pid_start(c.pid), rc=4)
        assert wait(tmp_path, str(c.pid)).returncode == 4
        # a stale record of an older process with this pid number does not answer for the live one
        rec_file(tmp_path, f"otrun-{S.host()}-{c.pid}", pid=c.pid, pid_start=1, rc=4)
        assert wait(tmp_path, str(c.pid), "--timeout", "1", "--poll", "0.2").returncode == 124
    finally:
        c.kill(); c.wait()


def test_begin_finish_and_unit(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_STATUS_DIR", str(tmp_path)); monkeypatch.setenv("OT_STATUS_POST", "0"); monkeypatch.delenv("OT_LANE", raising=False)
    rec = S.begin("run", "ot-run --mem 4 -- true")
    got = S.read(rec["name"])
    assert got["state"] == "running" and got["pid"] == os.getpid() and got["pid_start"]
    S.CURRENT = rec
    S.set_unit("oth-xyz")
    S.finish(rec, 7)
    got = S.read(rec["name"])
    assert got["state"] == "done" and got["rc"] == 7 and got["unit"] == "oth-xyz" and got["t_end"]


def test_run_recorded_passes_exit_through(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_STATUS_DIR", str(tmp_path)); monkeypatch.setenv("OT_STATUS_POST", "0")

    def boom():
        raise SystemExit(75)
    try:
        S.run_recorded("run", boom, "c")
    except SystemExit as e:
        assert e.code == 75
    f = [json.load(open(p)) for p in tmp_path.glob("otrun-*.json")]
    assert f and f[0]["rc"] == 75
    assert S.run_recorded("push", lambda: 4, "p") == 4
    assert [json.load(open(p))["rc"] for p in tmp_path.glob("otpush-*.json")] == [4]


def test_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_STATUS_DIR", str(tmp_path)); monkeypatch.setenv("OT_STATUS", "0")
    assert S.begin("run") is None and not list(tmp_path.iterdir())


def test_post_gating_and_text(tmp_path, monkeypatch):
    stub = tmp_path / "post.sh"
    out = tmp_path / "posted"
    stub.write_text(f'#!/bin/bash\necho "$1|$2" >> {out}\n')
    monkeypatch.setenv("OT_STATUS_DIR", str(tmp_path)); monkeypatch.setenv("OT_POST_SH", str(stub)); monkeypatch.setenv("OT_STATUS_POST", "1")
    base = dict(kind="run", name="otrun-h-1", unit="oth-1", host="h", lane="WAITER-STD-1600", cmd="bash proof.sh", log="/l.log", t_start=1000, t_end=1500)
    monkeypatch.delenv("OT_LANE", raising=False)
    assert S.post(dict(base, rc=2)) is None                      # run job from a lane that did not name itself: no post
    monkeypatch.setenv("OT_LANE", "WAITER-STD-1600")
    assert S.post(dict(base, rc=0, t_end=1010)) is None          # short DONE: no post
    argv = S.post(dict(base, rc=2))
    assert argv and argv[2] == "WAITER-STD-1600" and argv[3].startswith("DIED [WAITER-STD-1600] ot-run oth-1 on h: rc=2")
    argv = S.post(dict(base, rc=0))
    assert argv[3].startswith("DONE [WAITER-STD-1600]")
    push = dict(base, kind="push", name="otpush-h-1", unit="", rc=0, t_end=1002)
    monkeypatch.delenv("OT_LANE")
    assert S.post(push)[3].startswith("DONE [WAITER-STD-1600] ot-push-main")      # pushes post with the clone's lane
    monkeypatch.setenv("OT_STATUS_POST", "0")
    assert S.post(push) is None
    for _ in range(50):
        if out.exists() and len(out.read_text().splitlines()) >= 3:
            break
        time.sleep(0.1)
    assert len(out.read_text().splitlines()) == 3


def test_lane_from_dir(monkeypatch):
    monkeypatch.delenv("OT_LANE", raising=False)
    assert S.DIR_LANE.match("/srv/opentallas-scratch2/claude/FOO-1/ws/tools").group(1) == "FOO-1"
    assert S.lane_name("/srv/opentallas-scratch2/claude/rt/current/tools") == ""
    assert S.lane_name("/home/ubuntu") == ""


def test_ot_run_records_only_commands():
    M = SourceFileLoader("ot_run_status", str(HERE / "ot-run")).load_module()
    assert M._records_status(["--mem", "4", "--", "true"])
    for a in (["--status"], ["--cancel", "x"], ["--selftest"], ["--cancel-dir", "d"], ["--spill-sweep"], ["--mem", "4", "--pick", "--", "true"], []):
        assert not M._records_status(a)


def test_push_main_is_wrapped():
    src = (HERE / "ot-push-main").read_text()
    assert "run_recorded(\"push\"" in src and "sys.path.insert" in src


def test_pytest_children_do_not_record(tmp_path, monkeypatch):
    monkeypatch.delenv("OT_STATUS_DIR", raising=False)
    assert S.begin("run", "x") is None and not S.should_post(dict(kind="push", lane="L", rc=1, t_start=0, t_end=1))


def test_pid_wait_picks_up_record_written_late(tmp_path):
    c = subprocess.Popen(["sleep", "2"])
    # no record when ot-wait starts; the client writes one before it exits (start-up race of `ot-run ... & ot-wait $!`)
    rec_file(tmp_path, f"otrun-{S.host()}-{c.pid}", pid=c.pid, pid_start=S.pid_start(c.pid), rc=9)
    (tmp_path / f"otrun-{S.host()}-{c.pid}.json").rename(tmp_path / "late.json")
    p = subprocess.Popen([sys.executable, "-I", WAIT, str(c.pid), "--poll", "0.2"], stdout=subprocess.PIPE, text=True, env=env(tmp_path))
    time.sleep(0.5)
    (tmp_path / "late.json").rename(tmp_path / f"otrun-{S.host()}-{c.pid}.json")
    out, _ = p.communicate(timeout=30)
    c.wait()
    assert p.returncode == 9 and out.startswith("DIED rc=9")


def test_command_not_found_127_is_carried_not_zero(tmp_path):
    """FLEET-WATCH-2000: a job whose command exits 127 is DIED rc=127 and ot-wait returns 127 (GPL-TD-AB read DONE rc=0 because ab.sh ended with
    echo rc=? and a grep, so the script itself exited 0; the record and ot-wait carry the real exit status of whatever ot-run ran)."""
    rec_file(tmp_path, "otrun-h-127", rc=127, unit="oth-nf")
    p = wait(tmp_path, "otrun-h-127")
    assert p.returncode == 127 and p.stdout.startswith("DIED rc=127")


def kit_wait(tmp, *args, **kw):
    return wait(tmp, "--kit", *args, **kw)


def test_kit_stage_done_by_odb_not_log(tmp_path):
    kit = tmp_path / "kit"
    (kit / "run/results/asap7/dp_x/base").mkdir(parents=True)
    (kit / "run_route.log").write_text("route running\n")          # a route-goal kit: no run_place.log at all
    (kit / "run/results/asap7/dp_x/base/3_place.odb").write_text("odb")
    p = kit_wait(tmp_path, str(kit), "--stage", "place")
    assert p.returncode == 0 and p.stdout.startswith("DONE rc=0 kit=") and "3_place.odb" in p.stdout
    p = kit_wait(tmp_path, str(kit), "--stage", "cts", "--timeout", "1", "--poll", "0.2")
    assert p.returncode == 124


def test_kit_stage_fail_marker_and_missing_dir(tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "FAIL_POSTCTS").write_text("FAIL_POSTCTS FF structural hold gate: x\n")
    p = kit_wait(tmp_path, str(kit), "--stage", "route")
    assert p.returncode == 1 and "DIED rc=1" in p.stdout and "FAIL_POSTCTS" in p.stdout
    p = kit_wait(tmp_path, str(tmp_path / "nope"), "--stage", "place")
    assert p.returncode == 66


def test_kit_stage_also_ended_job_is_died(tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()
    rec_file(tmp_path, "otrun-h-9", rc=143, unit="oth-zz")
    p = kit_wait(tmp_path, str(kit), "--stage", "place", "--also", "otrun-h-9")
    assert p.returncode == 143 and "DIED rc=143" in p.stdout and "no place result" in p.stdout
