"""FLOW-FLEET-R1 (FABLE-FLOW-2200 A4 + COORD 11-22): tree copies hold a per-host copy slot, reuse a same-manifest tree already on the
host (ot-tree-fork --src-host, src_manifest replicate), and src_manifest verify ignores the .fork.json an ot-tree-fork copy carries."""
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TF = SourceFileLoader("ot_tree_fork_r", str(HERE / "ot-tree-fork")).load_module()
sys.path.insert(0, str(HERE.parent / "autopilot"))
import src_manifest as SM  # noqa: E402

FAKE_SSH = r'''#!/usr/bin/env python3
# stand-in for ssh: drop options and the host, run the joined words in bash (as ssh does); FAKE_MAP=a=b rewrites a path prefix
import os, subprocess, sys
args = sys.argv[1:]
while args and args[0].startswith("-"):
    args = args[2:] if args[0] in ("-o", "-p", "-l", "-i") else args[1:]
args = args[1:]
cmd = " ".join(args)
m = os.environ.get("FAKE_MAP", "")
if m:
    a, b = m.split("=", 1)
    cmd = cmd.replace(a, b)
with open(os.environ["FAKE_LOG"], "a") as f:
    f.write(cmd + "\n")
sys.exit(subprocess.run(["bash", "-c", cmd], env=dict(os.environ, HOME=os.environ.get("FAKE_HOME", os.environ["HOME"]))).returncode)
'''


def rmtree_ro(t):
    subprocess.run(["chmod", "-R", "u+w", str(t)], capture_output=True)
    shutil.rmtree(t, ignore_errors=True)


def manifest_tree(root, files):
    root = Path(root)
    for rel, txt in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(txt)
    m = {"main_sha": "abc", "scope": ["tools"], "overlay": {}, "files": {rel: SM.tree_hash(str(root / rel)) for rel in files}}
    m["manifest_hash"] = SM.manifest_hash(m)
    (root / SM.MANIFEST).write_text(json.dumps(m))
    (root / SM.HASHFILE).write_text(m["manifest_hash"] + "\n")
    return m["manifest_hash"]


@pytest.fixture
def env(tmp_path, monkeypatch):
    fake = tmp_path / "fake_ssh"
    fake.write_text(FAKE_SSH)
    fake.chmod(0o755)
    monkeypatch.setenv("FAKE_LOG", str(tmp_path / "ssh.log"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("OT_TREE_FORK_FLOOR_GB", "0")
    monkeypatch.setenv("OT_TREE_CACHE_ROOT", str(tmp_path / "cache"))
    monkeypatch.setenv("OT_TREE_INDEX", str(tmp_path / "home/trees.jsonl"))          # the remote side (script over the fake ssh) reads the env
    monkeypatch.setenv("OT_TREE_COPY_LOCK_DIR", str(tmp_path / "locks"))
    monkeypatch.setattr(TF, "LOG", str(tmp_path / "home/forks.jsonl"))
    monkeypatch.setattr(TF, "COPY_LOCK_DIR", str(tmp_path / "locks"))
    monkeypatch.setattr(TF, "TREE_INDEX", str(tmp_path / "home/trees.jsonl"))
    monkeypatch.setattr(TF, "SSH", [str(fake)])
    monkeypatch.setattr(SM, "COPY_LOCK_DIR", str(tmp_path / "locks"))
    monkeypatch.setattr(SM, "TREE_INDEX", str(tmp_path / "home/trees.jsonl"))
    monkeypatch.setattr(SM, "CACHE_DIR", str(tmp_path / "smcache"))
    yield tmp_path, fake
    rmtree_ro(tmp_path)


def test_verify_ignores_fork_json(env):
    t, _ = env
    tree = t / "fork"
    manifest_tree(tree, {"tools/a.py": "A=1\n"})
    (tree / ".fork.json").write_text("{}")
    assert SM.verify(str(tree), full=True)[0] == []
    (tree / "tools/stray.py").write_text("x")
    assert any("stray.py (extra" in e for e in SM.verify(str(tree), full=True)[0])


def test_copy_slots_are_shared_flock_files(env):
    t, _ = env
    a = TF.CopySlot(n=1, lock_dir=str(t / "locks"), wait_s=0, poll_s=0.01, out=lambda *_: None)
    with a:
        with pytest.raises(TF.Busy):
            with TF.CopySlot(n=1, lock_dir=str(t / "locks"), wait_s=0, poll_s=0.01, out=lambda *_: None):
                pass
        with TF.CopySlot(n=2, lock_dir=str(t / "locks"), wait_s=0, poll_s=0.01, out=lambda *_: None) as b:
            assert b.slot == 1
    # the shell prefix src_manifest puts in front of a remote rsync / tar holds the same slot files
    p = subprocess.Popen(["sh", "-c", SM.slot_sh(1, str(t / "locks")) + f"touch {t}/held; sleep 5"])
    try:
        for _ in range(100):
            if (t / "held").exists():
                break
            time.sleep(0.05)
        with pytest.raises(TF.Busy):
            with TF.CopySlot(n=1, lock_dir=str(t / "locks"), wait_s=0, poll_s=0.01, out=lambda *_: None):
                pass
    finally:
        p.kill()
        p.wait()


def test_src_host_fetches_once_then_reuses(env):
    t, _ = env
    src = t / "remote/kw45/T1"
    h = manifest_tree(src, {"tools/a.py": "A=1\n", "rtl/x.sv": "module x; endmodule\n"})
    SM.make_ro(str(src))
    out = []
    r1 = TF.fork_remote("hostS", str(src), str(t / "lane/claude/L1/tree"), out=out.append)
    assert r1["src_remote"] == f"hostS:{src}" and r1["reuse"].startswith("fetched")
    cache = t / "cache" / h[:16]
    assert TF.same_manifest(str(cache), h) == ""                      # read-only verified cache, indexed
    assert (t / "lane/claude/L1/tree/tools/a.py").read_text() == "A=1\n"
    assert os.lstat(t / "lane/claude/L1/tree/tools/a.py").st_nlink == 1
    n_ssh = len((t / "ssh.log").read_text().splitlines())
    r2 = TF.fork_remote("hostS", str(src), str(t / "lane/claude/L2/tree"), out=out.append)
    assert r2["reuse"] == "reused"
    log = (t / "ssh.log").read_text().splitlines()[n_ssh:]
    assert not any("tar -C" in l for l in log)                         # second fork: no network copy, only the hash read
    assert SM.verify(str(t / "lane/claude/L2/tree"), expect=h, full=True)[0] == []   # .fork.json ignored by the manifest check


def test_src_host_fetch_refuses_content_not_matching_manifest(env):
    t, _ = env
    src = t / "remote/T2"
    h = manifest_tree(src, {"tools/a.py": "A=1\n"})
    (src / "tools/a.py").write_text("A=2\n")                           # drifted source
    with pytest.raises(SystemExit, match="FETCH CHECK FAILED"):
        TF.fork_remote("hostS", str(src), str(t / "lane/claude/L3/tree"), out=lambda *_: None)
    assert not (t / "cache" / h[:16]).exists()


def test_src_host_without_manifest_fetches_into_the_fork(env):
    t, _ = env
    src = t / "remote/plain"
    (src / "d").mkdir(parents=True)
    (src / "d/f.txt").write_text("hi")
    (src / "d").chmod(0o550)
    os.symlink(str(src / "d/f.txt"), src / "abs")
    rec = TF.fork_remote("hostS", str(src), str(t / "lane/claude/L4/tree"), out=lambda *_: None)
    dst = t / "lane/claude/L4/tree"
    assert rec["method"] == "fetch" and (dst / "d/f.txt").read_text() == "hi"
    assert (dst / "d").stat().st_mode & 0o777 == 0o550
    assert os.readlink(dst / "abs") == "d/f.txt"                      # absolute link into SRC rewritten inside the fork
    assert json.loads((dst / ".fork.json").read_text())["src"] == f"hostS:{src}"


def test_same_tree_index(env):
    t, _ = env
    a = t / "trees/A"
    h = manifest_tree(a, {"tools/a.py": "A=1\n"})
    assert SM.same_tree(h) == ""
    SM.index_add(str(a))
    assert SM.same_tree(h) == ""                                       # writable: not published, never a base
    SM.make_ro(str(a))
    assert SM.same_tree(h) == str(a.resolve()) and SM.same_tree(h, exclude=str(a)) == ""
    assert TF.same_tree(h) == str(a.resolve())                         # both tools read the one index


def test_replicate_reuses_a_same_manifest_tree_on_the_target(env, monkeypatch):
    t, fake = env
    src_root, dst_root = t / "src", t / "dst"
    tree = src_root / "kw45/T9"
    h = manifest_tree(tree, {"tools/a.py": "A=1\n", "rtl/x.sv": "module x; endmodule\n"})
    SM.publish(str(tree))
    other = dst_root / "lanes/copyB"                                   # the target already holds the same manifest at another path
    manifest_tree(other, {"tools/a.py": "A=1\n", "rtl/x.sv": "module x; endmodule\n"})
    SM.make_ro(str(other))
    (dst_root / "kw45").mkdir(parents=True)
    SM.index_add(str(other))
    monkeypatch.setenv("FAKE_MAP", f"{src_root}/={dst_root}/")
    monkeypatch.setattr(SM, "SSH", [str(fake)])
    monkeypatch.setattr(SM, "RSYNC_SSH", str(fake))
    monkeypatch.setattr(SM, "REPL_FLOOR_GB", 0)
    assert SM.main(["replicate", str(tree), "--hosts", "h"]) == 0
    got = dst_root / "kw45/T9"
    assert SM.verify(str(got), expect=h, ro=True, full=True)[0] == []
    assert os.lstat(got / "tools/a.py").st_ino == os.lstat(other / "tools/a.py").st_ino   # made from the local tree, no data copied
    assert not any(l.startswith("rsync") and "--server" in l for l in (t / "ssh.log").read_text().splitlines())
