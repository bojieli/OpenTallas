"""P-LAUNCH-SETUP-FAIL: ot-push-main always logs and names the reason of every nonzero exit."""
import os
import subprocess
import sys
from pathlib import Path

PUSH = str(Path(__file__).with_name("ot-push-main"))


def run(tmp, args, cwd, log=True):
    env = dict(os.environ, HOME=str(tmp), GIT_CEILING_DIRECTORIES=str(Path(cwd).parent))
    env.pop("OT_PUSH_LOG", None)
    if log:
        env["OT_PUSH_LOG"] = str(tmp / "push.log")
    return subprocess.run([sys.executable, "-I", PUSH, *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=120)


def test_not_a_git_clone_rc2_reason_and_log(tmp_path):
    cwd = tmp_path / "plain"
    cwd.mkdir()
    r = run(tmp_path, [], cwd)
    assert r.returncode == 2
    assert "ot-push-main: log %s" % (tmp_path / "push.log") in r.stderr
    assert "ot-push-main: rc 2: not inside a git clone" in r.stdout + r.stderr
    txt = (tmp_path / "push.log").read_text()
    assert "rc 2: not inside a git clone" in txt


def test_bad_flag_rc2_reason_and_log(tmp_path):
    cwd = tmp_path / "plain"
    cwd.mkdir()
    r = run(tmp_path, ["--no-such-flag"], cwd)
    assert r.returncode == 2
    assert "ot-push-main: rc 2: usage error: unrecognized arguments: --no-such-flag" in r.stderr
    txt = (tmp_path / "push.log").read_text()
    assert "rc 2: usage error" in txt and "--no-such-flag" in txt


def test_default_log_path_and_dirty_clone(tmp_path):
    cwd = tmp_path / "repo"
    cwd.mkdir()
    g = lambda *a: subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True)
    g("init", "-q")
    (cwd / "f").write_text("1")
    g("add", "f")
    g("commit", "-q", "-m", "x")
    (cwd / "f").write_text("2")
    r = run(tmp_path, [], cwd, log=False)
    assert r.returncode == 2 and "rc 2: uncommitted changes" in r.stdout + r.stderr
    first = r.stderr.splitlines()[0]
    assert first.startswith("ot-push-main: log /tmp/ot-push-main.")
    lp = Path(first.split("log ", 1)[1])
    assert lp.is_file() and "rc 2: uncommitted changes" in lp.read_text()
    lp.unlink()
