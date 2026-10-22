"""sparse_keep: widening a sparse worktree never deletes on-disk kits (TOKc-SPARSE 2026-10-22).

Reproduces the 10-22 S81 TOPK TX loss: kit x is committed in a sparse worktree but not in its list; a plain
`git sparse-checkout add <kit ga>` (the submit waiter) deletes x from disk.  sparse_keep.add must keep it."""
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
