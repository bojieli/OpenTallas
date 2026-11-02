"""KIT-WAVE-15 11-01 (COORD 18:2x disk class): source-follow snapshots cost only the delta (hard links into the
previous snapshot, git writes changed files as new inodes) and old unreferenced snapshots are retired.
Runs under pytest or as a plain script (the hub has no pytest)."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_follow as S  # noqa: E402

GIT = ["git", "-c", "user.email=t@t", "-c", "user.name=t"]


def sh(*a, cwd=None):
    return subprocess.run(list(a), cwd=cwd, check=True, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT).stdout


def make_repo(t):
    repo = t / "repo"
    repo.mkdir()
    sh("git", "init", "-q", str(repo))
    for rel, body in {"rtl/a.sv": "a\n", "rtl/b.sv": "b\n", "rtl/gone.sv": "g\n", "tools/t.py": "t\n",
                      "other/big.bin": "o\n"}.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(body)
    sh(*GIT, "-C", str(repo), "add", "-A")
    sh(*GIT, "-C", str(repo), "commit", "-qm", "A")
    a = sh("git", "-C", str(repo), "rev-parse", "HEAD").strip()
    (repo / "rtl/b.sv").write_text("b changed\n")
    (repo / "rtl/new.sv").write_text("n\n")
    (repo / "rtl/gone.sv").unlink()
    sh(*GIT, "-C", str(repo), "add", "-A")
    sh(*GIT, "-C", str(repo), "commit", "-qm", "B")
    b = sh("git", "-C", str(repo), "rev-parse", "HEAD").strip()
    return repo, a, b


def snapshot(repo, die_root, sha, cone=("rtl", "tools"), delta=True):
    root = die_root / sha[:12]
    src = root / "src"
    root.mkdir(parents=True)
    sh("git", "-C", str(repo), "worktree", "add", "-q", "--detach", "--no-checkout", str(src), sha)
    sh("git", "-C", str(src), "sparse-checkout", "init", "--cone")
    sh("git", "-C", str(src), "sparse-checkout", "set", *cone)
    prev, linked = S.link_previous_snapshot(repo, src, sha, list(cone), die_root) if delta else (None, 0)
    if linked:
        S.finish_linked_checkout(src)
    else:
        sh("git", "-C", str(src), "checkout", "-q")
    (root / "source_checkout.ready").write_text(sha + "\n")
    return src, prev, linked


def test_delta_snapshot_links_unchanged_and_isolates_changed():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        repo, a, b = make_repo(t)
        die_root = t / "sf" / "qwen_kvsys"
        old, _, n0 = snapshot(repo, die_root, a)
        assert n0 == 0
        time.sleep(0.01)
        new, prev, n = snapshot(repo, die_root, b)
        assert prev == old and n == 2                         # rtl/a.sv + tools/t.py
        assert os.stat(new / "rtl/a.sv").st_ino == os.stat(old / "rtl/a.sv").st_ino
        assert os.stat(new / "rtl/b.sv").st_ino != os.stat(old / "rtl/b.sv").st_ino
        assert (old / "rtl/b.sv").read_text() == "b\n" and (new / "rtl/b.sv").read_text() == "b changed\n"
        assert (new / "rtl/new.sv").read_text() == "n\n" and not (new / "rtl/gone.sv").exists()
        assert (old / "rtl/gone.sv").exists()                  # previous snapshot untouched
        assert not (new / "other").exists()                    # sparse cone kept
        assert sh("git", "-C", str(new), "status", "--porcelain", "--untracked-files=no") == ""
        assert sh("git", "-C", str(new), "rev-parse", "HEAD").strip() == b


def test_linked_files_read_only_and_replacement_keeps_sibling():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        repo, a, b = make_repo(t)
        die_root = t / "sf" / "qwen_kvsys"
        old, _, _ = snapshot(repo, die_root, a)
        new, _, n = snapshot(repo, die_root, b)
        assert n == 2
        for snap in (old, new):                               # shared inode: read-only in both snapshots
            assert not os.stat(snap / "rtl/a.sv").st_mode & 0o222
        assert os.stat(new / "rtl/b.sv").st_mode & 0o200        # a file git wrote fresh stays writable
        if os.geteuid() != 0:                                   # root ignores mode bits
            try:
                open(new / "rtl/a.sv", "w").write("corrupt\n")
                raise AssertionError("in-place write through a linked file succeeded")
            except PermissionError:
                pass
        # The source-follow steps after linking only create new files: they do not touch linked paths.
        (old / "rtl/untracked_input.json").write_text("{}")
        assert S.copy_untracked_inputs(old, new) == ["rtl/untracked_input.json"]
        assert os.stat(new / "rtl/a.sv").st_ino == os.stat(old / "rtl/a.sv").st_ino
        # A git step in the new snapshot that replaces a linked path writes a fresh inode; the sibling keeps its bytes.
        (repo / "rtl/a.sv").write_text("a changed later\n")
        sh(*GIT, "-C", str(repo), "commit", "-qam", "C")
        c = sh("git", "-C", str(repo), "rev-parse", "HEAD").strip()
        sh("git", "-C", str(new), "checkout", "-q", "--detach", c)
        assert (new / "rtl/a.sv").read_text() == "a changed later\n"
        assert (old / "rtl/a.sv").read_text() == "a\n"
        assert os.stat(new / "rtl/a.sv").st_ino != os.stat(old / "rtl/a.sv").st_ino
        assert sh("git", "-C", str(old), "status", "--porcelain", "--untracked-files=no") == ""


def test_link_base_is_newest_complete_snapshot():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        repo, a, b = make_repo(t)
        die_root = t / "sf" / "s81"
        old, _, _ = snapshot(repo, die_root, a)
        (die_root / ("f" * 12) / "src").mkdir(parents=True)   # incomplete snapshot: no ready marker, no .git
        new, prev, n = snapshot(repo, die_root, b)
        assert prev == old and n == 2


def test_retention_keep_set():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        repo, a, b = make_repo(t)
        die_root = t / "sf" / "qwen_kvsys"
        names = ["%012x" % i for i in range(1, 6)]
        for i, nm in enumerate(names):
            (die_root / nm).mkdir(parents=True)
            r = die_root / nm / "source_checkout.ready"
            r.write_text("x\n")
            os.utime(r, (1000 + i, 1000 + i))
        wt_old, _, _ = snapshot(repo, die_root, a, delta=False)   # a real worktree snapshot, made last ...
        os.utime(wt_old.parent / "source_checkout.ready", (10, 10))  # ... but the oldest
        (die_root / "notes").mkdir()                            # not a snapshot name: never a candidate
        current = die_root / names[0]
        refs = ["src " + str(die_root / names[1]) + "/rtl/x.sv", str(die_root / names[2]) + "x"]
        assert S.prune_snapshots(repo, die_root, None, current) == []
        removed = S.prune_snapshots(repo, die_root, refs, current, newest=2, log=lambda m: None)
        left = sorted(p.name for p in die_root.iterdir())
        # newest 2 = names[4], names[3]; current = names[0]; referenced = names[1]; names[2] ref is a prefix only
        assert left == sorted([names[0], names[1], names[3], names[4], "notes"]), left
        assert str(wt_old.parent) in removed and str(die_root / names[2]) in removed
        assert str(wt_old) not in sh("git", "-C", str(repo), "worktree", "list")


def test_live_refs_and_referenced_snapshots():
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        ap = t / "coord" / "autopilot"
        ap.mkdir(parents=True)
        root = "/sf/qwen_kvsys"
        items = {}
        for k, (st, qs, sha) in {"r": ("RUNNING", None, "a" * 12), "e": ("ENQUEUED", "RUNNING", "b" * 12),
                                 "f": ("ENQUEUED", "FAIL", "c" * 12), "x": ("FAIL", None, "d" * 12)}.items():
            d = t / k
            d.mkdir()
            (d / "spec.json").write_text(json.dumps({"src": root + "/" + sha + "/src"}))
            items[k] = {"status": st, "q_status": qs, "dir": str(d)}
        (ap / "kit_wave_state.json").write_text(json.dumps({"items": items}))
        (ap.parent / "PROTECTED-DBS.txt").write_text(root + "/" + "e" * 12 + "/bind\n")
        cfg = {"dies": {"qwen_kvsys": {"src": root + "/" + "1" * 12 + "/src"}}}
        state = {"source_follow": {"qwen_kvsys": {"ready": {"src": root + "/" + "2" * 12 + "/src"}}}}
        got = S.referenced_snapshots(S.live_snapshot_refs(ap, cfg, state), root)
        assert got == sorted(root + "/" + c * 12 for c in "12abe"), got
        assert S.live_snapshot_refs(t / "missing", cfg, state) is None
        assert S.referenced_snapshots(None, root) is None


def test_payload_compiles_with_helpers():
    import inspect
    src = "\n".join(inspect.getsource(f) for f in (S.materialize_clock_mesh, S.copy_untracked_inputs,
                                                   S.link_previous_snapshot, S.finish_linked_checkout,
                                                   S.prune_snapshots, S.same_library_interface,
                                                   S.used_hdl_paths)) + "\n" + S.REMOTE
    compile(src, "payload", "exec")
    assert "link_previous_snapshot(repo,src,tip,cone,root.parent)" in S.REMOTE
    assert "prune_snapshots(repo,root.parent" in S.REMOTE


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as e:  # noqa: BLE001
                fails += 1
                print("FAIL", name, repr(e))
    sys.exit(1 if fails else 0)
