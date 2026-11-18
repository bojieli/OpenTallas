"""COORD 11-18: ot-heavy admission breaks an admit.lock whose holder pid is gone (a leaked inherited fd kept the flock for 70 min on epyc7)."""
import os, pathlib, subprocess, tempfile, textwrap, time

OT = pathlib.Path(__file__).with_name("ot-heavy")


def fn_source():
    t = OT.read_text()
    i = t.index("ot_heavy_admit_lock() {")
    j = t.index("\n}\n", i) + 3
    return t[i:j]


def run_lock(d, wait="2", unit="oth-test-1"):
    script = textwrap.dedent("""
        D=%s; UNIT=%s; export OT_HEAVY_LOCK_WAIT_S=%s
        %s
        ot_heavy_admit_lock && echo GOT && cat $D/admit.lock.pid
    """) % (d, unit, wait, fn_source())
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=40)


def test_free_lock_is_taken_and_the_pid_recorded(tmp_path):
    r = run_lock(str(tmp_path))
    assert r.returncode == 0 and "GOT" in r.stdout and r.stdout.split()[-1].isdigit()


def test_a_lock_held_through_a_leaked_fd_with_a_dead_holder_is_broken(tmp_path):
    d = str(tmp_path)
    # the holder takes the lock, records its pid and EXITS; a background child keeps fd 8 (the leak)
    subprocess.run(["bash", "-c", "( exec 8>>%s/admit.lock; flock 8; echo $BASHPID > %s/admit.lock.pid; sleep 25 8>&8 & ) ; sleep 0.2" % (d, d)], timeout=10)
    t0 = time.time()
    r = run_lock(d, wait="2")
    assert "GOT" in r.stdout, r.stdout + r.stderr
    assert time.time() - t0 < 15                                             # not the 25 s the leak would last, nor 70 min
    assert "STALE-LOCK" in (tmp_path / "admit.log").read_text()


def test_a_live_holder_is_waited_for_not_broken(tmp_path):
    d = str(tmp_path)
    holder = subprocess.Popen(["bash", "-c", "exec 8>>%s/admit.lock; flock 8; echo $$ > %s/admit.lock.pid; sleep 6" % (d, d)])
    time.sleep(0.5)
    r = run_lock(d, wait="1")
    holder.wait()
    assert "GOT" in r.stdout
    assert not (tmp_path / "admit.log").exists() or "STALE-LOCK" not in (tmp_path / "admit.log").read_text()
