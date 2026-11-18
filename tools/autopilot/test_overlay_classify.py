"""WAVE-FLOW-R2 11-17 (COORD r610): overlay paths main also changed are classified (a) blob in main's history, (b) change contained in main, (c) private."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import overlay_classify as OC


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True, text=True).stdout.strip()


def commit(repo, files, msg):
    for rel, text in files.items():
        f = Path(repo) / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        if text is None:
            f.unlink()
        else:
            f.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


V1 = "def f():\n    return 1\n\n\ndef g():\n    return 'g'\n"
V2 = "def f():\n    return 2\n\n\ndef g():\n    return 'g'\n"
V3 = "def f():\n    return 2\n\n\ndef g():\n    return 'g'\n\n\ndef h():\n    return 3\n"


def make(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    base = commit(r, {"tools/a.py": V1, "tools/b.py": V1, "tools/c.py": V1, "tools/d.py": V1, "tools/e.py": V1, "tools/untouched.py": V1, "rtl/x.sv": "a\n"}, "base")
    commit(r, {"tools/a.py": V2, "tools/b.py": V3, "tools/c.py": V3, "tools/d.py": None, "tools/e.py": "other\n", "rtl/x.sv": "b\n"}, "main moves")
    commit(r, {"tools/a.py": V3}, "a again")                 # a's overlay (V2) is an OLDER version in main's history
    return r / ".git", base


def test_classification(tmp_path):
    repo, base = make(tmp_path)
    overlay = {"tools/a.py": V2.encode(),                                                   # (a) equals a version in history
               "tools/b.py": V2.encode(),                                                   # (b) its change (return 1 -> 2) ... see below
               "tools/c.py": (V1 + "\n\ndef private():\n    return 'mine'\n").encode(),    # (c) a patch main does not have
               "tools/d.py": (V1 + "# mine\n").encode(),                                    # (c) main deleted the file
               "tools/e.py": b"other\n",                                                    # (a) blob equal to main's current
               "tools/untouched.py": (V1 + "# patched\n").encode(), "rtl/x.sv": b"z\n"}
    manifest = {"main_sha": base, "overlay": {p: "x" for p in overlay}}
    res = OC.classify_tree(repo, manifest, lambda paths: {p: overlay.get(p) for p in paths}, "main")
    assert sorted(res) == ["tools/a.py", "tools/b.py", "tools/c.py", "tools/d.py", "tools/e.py"]      # untouched.py: main never changed it; rtl/: outside the pack
    assert res["tools/a.py"]["cls"] == "a" and res["tools/e.py"]["cls"] == "a"
    assert res["tools/b.py"]["cls"] in ("a", "b")                                           # V2 is also in b's own history? no: b was V1 -> V3; the change return 2 is in V3
    assert res["tools/c.py"]["cls"] == "c" and "+def private" in res["tools/c.py"]["diff"]
    assert res["tools/d.py"]["cls"] == "c" and "deleted" in res["tools/d.py"]["why"]
    assert OC.counts(res) == {"a": 2, "b": 1, "c": 2} or OC.counts(res) == {"a": 3, "b": 0, "c": 2}


def test_contained_and_deletion_semantics():
    base, over = V1.splitlines(), V2.splitlines()
    assert OC.contained(base, over, V3.splitlines())                                       # main has the replacement block
    assert not OC.contained(base, over, V1.splitlines())                                   # main still has the old text
    assert not OC.contained(base, V1.splitlines()[:3], V1.splitlines())                    # a deletion main did not make
    assert OC.blob_sha1(b"abc") == "f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f"              # git hash-object of "abc"


def test_overlay_byte_equal_to_main_head_is_a_even_when_the_blob_only_exists_in_a_merge(tmp_path):
    """r612 (QC-PLAN-R3): signoff.py / hold_eco_internal_insert.tcl / ot-merge-queue were byte-equal to main HEAD yet classed (c): the main blob came in
    through a hand-resolved merge commit, so `git log --raw` (no -m) never listed it"""
    r = tmp_path / "repo2"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    base = commit(r, {"tools/s.py": "a=1\nb=2\nc=3\n"}, "base")
    git(r, "checkout", "-q", "-b", "side")
    commit(r, {"tools/s.py": "a=1\nb=2\nc=SIDE\n"}, "side change")
    git(r, "checkout", "-q", "main")
    commit(r, {"tools/s.py": "a=MAIN\nb=2\nc=3\n"}, "main change")
    subprocess.run(["git", "-C", str(r), "-c", "user.name=t", "-c", "user.email=t@t", "merge", "-q", "--no-commit", "side"], capture_output=True)
    resolved = "a=MAIN\nb=2\nc=SIDE\n"                               # hand-resolved: equals neither parent
    (r / "tools/s.py").write_text(resolved)
    git(r, "add", "-A")
    git(r, "commit", "-q", "-m", "Merge side (hand-resolved)")
    repo = r / ".git"
    manifest = {"main_sha": base, "overlay": {"tools/s.py": "x"}}
    plain = OC.git(repo, "log", f"{base}..main", "--format=", "--raw", "--no-abbrev", "--", "tools").decode()
    assert OC.blob_sha1(resolved.encode()) not in plain                          # the bug: a plain log does not list the merge-only blob
    res = OC.classify_tree(repo, manifest, lambda paths: {p: resolved.encode() for p in paths}, "main")
    assert res["tools/s.py"]["cls"] == "a" and "byte-equal" in res["tools/s.py"]["why"]
    assert OC.blob_sha1(resolved.encode()) in OC.blob_history(repo, "main", ["tools/s.py"], since=base)["tools/s.py"]     # -m lists it
    older = commit(r, {"tools/s.py": "later\n"}, "later")
    res = OC.classify_tree(repo, manifest, lambda paths: {p: resolved.encode() for p in paths}, "main")
    assert res["tools/s.py"]["cls"] == "a" and "history" in res["tools/s.py"]["why"]      # an older merge-only version still counts (a)
