"""sparse_keep: widening a sparse worktree never deletes on-disk kits (TOKc-SPARSE 2026-10-22).

Reproduces the 10-22 S81 TOPK TX loss: kit x is committed in a sparse worktree but not in its list; a plain
`git sparse-checkout add <kit ga>` (the submit waiter) deletes x from disk.  sparse_keep.add must keep it."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sparse_keep as K  # noqa: E402

KITS = ("physical/ref_tile/kga", "physical/ref_tile/kx", "physical/ref_tile/kother")


def g(d, *a):
    return subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True, text=True).stdout


def make(tmp_path, cone):
    repo = tmp_path / "repo"
    repo.mkdir()
    g(repo, "init", "-q")
    g(repo, "config", "user.email", "t@t")
    g(repo, "config", "user.name", "t")
    for d in ("tools", "rtl", *KITS):
        (repo / d).mkdir(parents=True)
        (repo / d / "f.json").write_text(d)
    (repo / "physical/ref_tile/kx/sub").mkdir()
    (repo / "physical/ref_tile/kx/sub/g").write_text("g")
    (repo / "physical/ref_tile/top.json").write_text("{}")
    g(repo, "add", "-A")
    g(repo, "commit", "-qm", "init")
    # the shared checkout's config: sparse on, non-cone default, per-worktree config
    g(repo, "config", "core.sparseCheckout", "true")
    g(repo, "config", "core.sparseCheckoutCone", "false")
    g(repo, "config", "extensions.worktreeConfig", "true")
    wt = tmp_path / "wt"
    g(repo, "worktree", "add", "-q", "--no-checkout", str(wt), "-b", "b")
    if cone:
        g(wt, "config", "--worktree", "core.sparseCheckoutCone", "true")
        g(wt, "sparse-checkout", "set", "tools", "physical/ref_tile/kga")
    else:
        g(wt, "sparse-checkout", "set", "/tools/", "/physical/ref_tile/kga/")
    g(wt, "checkout", "-q", "b")
    # kit x materialized and tracked but never listed (what a hand-materialized / --sparse-added kit looks like)
    g(wt, "update-index", "--no-skip-worktree", *[p for p in g(wt, "ls-files", "physical/ref_tile/kx").split()])
    g(wt, "checkout-index", "-f", "--", *[p for p in g(wt, "ls-files", "physical/ref_tile/kx").split()])
    subprocess.run(["git", "-C", str(wt), "update-index", "-q", "--refresh"], capture_output=True)   # clean stat
    assert (wt / "physical/ref_tile/kx/f.json").is_file() and (wt / "physical/ref_tile/kx/sub/g").is_file()
    return repo, wt


def patterns(wt):
    return [ln for ln in K.sparse_file(wt).read_text().splitlines() if ln.strip()]


@pytest.mark.parametrize("cone", [False, True])
def test_plain_add_deletes_unlisted_kit(tmp_path, cone):
    """the bug: git's own add re-applies the list and removes the unlisted kit x"""
    _, wt = make(tmp_path, cone)
    assert K.at_risk(wt) == ["physical/ref_tile/kx/f.json", "physical/ref_tile/kx/sub/g"]
    g(wt, "sparse-checkout", "add", "rtl" if cone else "/rtl/")
    assert not (wt / "physical/ref_tile/kx/f.json").exists()


@pytest.mark.parametrize("cone", [False, True])
def test_sparse_keep_add_keeps_both_kits(tmp_path, cone):
    _, wt = make(tmp_path, cone)
    before = patterns(wt)
    rc, msg = K.add(wt, ["physical/ref_tile/kother/"])
    assert rc == 0, msg
    for k in ("kga", "kx", "kother"):
        assert (wt / f"physical/ref_tile/{k}/f.json").is_file(), (k, msg)
    assert (wt / "physical/ref_tile/kx/sub/g").is_file()
    after = patterns(wt)
    assert all(p in after for p in before) and len(after) >= len(before)
    assert K.at_risk(wt) == []
    # a later plain git add (another agent's waiter) no longer deletes x
    g(wt, "sparse-checkout", "add", "rtl" if cone else "/rtl/")
    assert (wt / "physical/ref_tile/kx/f.json").is_file() and (wt / "physical/ref_tile/kga/f.json").is_file()


@pytest.mark.parametrize("cone", [False, True])
def test_protect_then_check_clean(tmp_path, cone):
    _, wt = make(tmp_path, cone)
    assert K.main(["check", str(wt)]) == 1
    assert K.main(["protect", str(wt)]) == 0
    assert K.main(["check", str(wt)]) == 0
    assert (wt / "physical/ref_tile/kx/sub/g").is_file()
    assert not (wt / "physical/ref_tile/kother/f.json").exists()      # protection materializes nothing new


@pytest.mark.parametrize("cone", [False, True])
def test_lone_file_in_skipped_dir(tmp_path, cone):
    """rtl/f.json on disk, rtl/ also holds a skipped file: cone mode cannot protect it without materializing rtl/;
    it refuses and changes nothing.  Non-cone protects the single file."""
    repo, wt = make(tmp_path, cone)
    (repo / "rtl/g.sv").write_text("g")
    g(repo, "add", "rtl/g.sv")
    g(repo, "commit", "-qm", "g")
    g(wt, "merge", "-q", "--ff-only", "master" if "master" in g(repo, "branch") else "main")
    K.main(["protect", str(wt)])
    g(wt, "update-index", "--no-skip-worktree", "rtl/f.json")
    g(wt, "checkout-index", "-f", "--", "rtl/f.json")
    subprocess.run(["git", "-C", str(wt), "update-index", "-q", "--refresh"], capture_output=True)
    before = patterns(wt)
    rc, msg = K.add(wt, [])
    assert (wt / "rtl/f.json").is_file()
    if cone:
        assert rc == 1 and "REFUSED" in msg and patterns(wt) == before
    else:
        assert rc == 0, msg
        assert not (wt / "rtl/g.sv").exists() and K.at_risk(wt) == []


def test_matcher_cone_format():
    pats = K.parse_patterns("/*\n!/*/\n/physical/\n!/physical/*/\n/physical/ref_tile/\n!/physical/ref_tile/*/\n"
                            "/physical/ref_tile/kga/\n--no-cone\n")
    assert K.included(pats, "README")
    assert K.included(pats, "physical/ref_tile/top.json")
    assert K.included(pats, "physical/ref_tile/kga/a/b")
    assert not K.included(pats, "physical/ref_tile/kx/f.json")
    assert not K.included(pats, "rtl/x.sv")
    nc = K.parse_patterns("/tools/\n/physical/ref_tile/k*/\n!/physical/ref_tile/kq/\n**/keep.me\n")
    assert K.included(nc, "tools/a/b.py") and K.included(nc, "physical/ref_tile/kx/f")
    assert not K.included(nc, "physical/ref_tile/kq/f") and K.included(nc, "deep/x/keep.me")


# ---------------------------------------------------------------------------------------------- 10-22 append-only fix
def _negrepo(tmp_path):
    """non-cone worktree whose list carries negatives + a comment (the codex-qw-a0-kfirst/localreq shape)"""
    repo, wt = make(tmp_path, False)
    for f in ("tools/x/a.py", "tools/x/drop/f", "tools/x/keep/f", "tools/x/rc14/f"):
        (repo / f).parent.mkdir(parents=True, exist_ok=True)
        (repo / f).write_text(f)
    g(repo, "add", "-A")
    g(repo, "commit", "-qm", "x")
    g(wt, "merge", "-q", "--ff-only", "master" if "master" in g(repo, "branch") else "main")
    sf = K.sparse_file(wt)
    lines = sf.read_text().splitlines() + ["# keep me", "!/tools/x/*/", "/tools/x/keep/", "/tools/x/rc14/"]
    sf.write_text("\n".join(lines) + "\n")
    g(wt, "sparse-checkout", "reapply")
    assert not (wt / "tools/x/drop/f").exists() and (wt / "tools/x/rc14/f").is_file()
    kx = g(wt, "ls-files", "physical/ref_tile/kx").split()        # the reapply above removed kit x: re-materialize
    g(wt, "update-index", "--no-skip-worktree", *kx)
    g(wt, "checkout-index", "-f", "--", *kx)
    subprocess.run(["git", "-C", str(wt), "update-index", "-q", "--refresh"], capture_output=True)
    assert K.at_risk(wt) == ["physical/ref_tile/kx/f.json", "physical/ref_tile/kx/sub/g"]
    return repo, wt, sf.read_text()


@pytest.mark.parametrize("cmd", ["add", "protect"])
def test_noncone_negatives_kept_verbatim(tmp_path, cmd):
    _, wt, before = _negrepo(tmp_path)
    args = [cmd, str(wt)] + (["rtl/"] if cmd == "add" else [])
    assert K.main(args) == 0
    after = K.sparse_file(wt).read_text()
    assert after.startswith(before), after               # every old line, same order, negatives and comment intact
    assert len(after.splitlines()) > len(before.splitlines())
    assert (wt / "tools/x/keep/f").is_file() and (wt / "tools/x/rc14/f").is_file() and (wt / "tools/x/a.py").is_file()
    assert not (wt / "tools/x/drop/f").exists()
    assert (wt / "physical/ref_tile/kx/sub/g").is_file()
    assert (cmd != "add") or (wt / "rtl/f.json").is_file()


def test_untracked_and_ignored_in_losing_dir_refuse(tmp_path):
    """a cone list whose a/sub/ entry lacks its parent: appending a valid cone parent for a/other narrows a/sub;
    the untracked + ignored files there make sparse_keep refuse with nothing changed"""
    repo, wt = make(tmp_path, True)
    (repo / ".gitignore").write_text("*.log\n")
    (repo / "a/other").mkdir(parents=True)
    (repo / "a/other/f").write_text("f")
    g(repo, "add", "-A")
    g(repo, "commit", "-qm", "a")
    g(wt, "merge", "-q", "--ff-only", "master" if "master" in g(repo, "branch") else "main")
    sf = K.sparse_file(wt)
    sf.write_text(sf.read_text() + "/a/sub/\n")
    (wt / "a/sub").mkdir(parents=True)
    (wt / "a/sub/u.txt").write_text("u")
    (wt / "a/sub/i.log").write_text("i")
    before = sf.read_text()
    rc, msg = K.add(wt, ["a/other"])
    assert rc == 1 and "REFUSED" in msg and "untracked" in msg, msg
    assert sf.read_text() == before
    assert (wt / "a/sub/u.txt").is_file() and (wt / "a/sub/i.log").is_file() and not (wt / "a/other/f").exists()


def test_full_checkout_and_unreadable_list_are_noops(tmp_path):
    repo, wt = make(tmp_path, False)
    sf = K.sparse_file(wt)
    # 1) all of HEAD on disk though core.sparseCheckout=true and the list is narrow (qkc-cb16 / sqc-iof shape)
    g(wt, "sparse-checkout", "disable")
    g(wt, "config", "--worktree", "core.sparseCheckout", "true")
    sf.write_text("/tools/\n")
    assert K.main(["protect", str(wt)]) == 0 and K.main(["add", str(wt), "rtl/"]) == 0
    assert sf.read_text() == "/tools/\n" and (wt / "rtl/f.json").is_file()
    # 2) missing list (qkc-grp-1021 shape)
    sf.unlink()
    assert K.main(["protect", str(wt)]) == 0 and K.main(["add", str(wt), "rtl/"]) == 0 and not sf.exists()
    # 3) unreadable list on a really sparse worktree
    (tmp_path / "two").mkdir()
    _, wt2 = make(tmp_path / "two", False)
    sf2 = K.sparse_file(wt2)
    keep = sf2.read_text()
    sf2.chmod(0)
    try:
        if os.access(sf2, os.R_OK):
            pytest.skip("running as root: chmod 0 does not block reads")
        assert K.main(["protect", str(wt2)]) == 0 and K.main(["add", str(wt2), "rtl/"]) == 0
    finally:
        sf2.chmod(0o644)
    assert sf2.read_text() == keep
    # 4) core.sparseCheckout false
    g(wt2, "config", "--worktree", "core.sparseCheckout", "false")
    assert K.main(["protect", str(wt2)]) == 0 and sf2.read_text() == keep
