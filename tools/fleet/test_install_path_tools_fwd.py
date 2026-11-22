"""FLOW-OPS-1300 item 14: install_path_tools.sh on a host without rt/current writes an ot-wait forwarder to the hub (args quoted, exit passed)."""
import os, pathlib, stat, subprocess

HERE = pathlib.Path(__file__).resolve().parent


def test_forwarder_on_host_without_rt(tmp_path):
    b = tmp_path / "bin"
    env = dict(os.environ, OT_RT=str(tmp_path / "no-rt"), OT_BIN=str(b), OT_WAIT_HUB="hubx")
    r = subprocess.run(["bash", str(HERE / "install_path_tools.sh")], capture_output=True, text=True, env=env, timeout=60)
    assert r.returncode == 0 and "forwarder to hubx" in r.stdout
    w = b / "ot-wait"
    assert w.stat().st_mode & stat.S_IXUSR
    t = w.read_text()
    assert t.startswith("#!/bin/bash") and "OT_WAIT_HUB:-hubx" in t
    fake = tmp_path / "fake"
    fake.mkdir()
    (fake / "ssh").write_text('#!/bin/bash\nfor a in "$@"; do echo "ARG<$a>"; done\nexit 7\n')
    (fake / "ssh").chmod(0o755)
    r = subprocess.run([str(w), "oth-a b", "--timeout", "60"], capture_output=True, text=True,
                       env=dict(os.environ, PATH=f"{fake}:/usr/bin:/bin"), timeout=60)
    assert r.returncode == 7
    assert "ARG<hubx>" in r.stdout and "ARG<ot-wait oth-a\\ b --timeout 60>" in r.stdout


def test_symlinks_when_rt_exists(tmp_path):
    rt = tmp_path / "rt" / "tools" / "fleet"
    rt.mkdir(parents=True)
    for t in ("ot-wait", "ot_status.py", "ot_delete_guard.py"):
        (rt / t).write_text("x")
    b = tmp_path / "bin"
    env = dict(os.environ, OT_RT=str(tmp_path / "rt"), OT_BIN=str(b))
    r = subprocess.run(["bash", str(HERE / "install_path_tools.sh")], capture_output=True, text=True, env=env, timeout=60)
    assert r.returncode == 0
    assert os.readlink(b / "ot-wait") == str(rt / "ot-wait")
