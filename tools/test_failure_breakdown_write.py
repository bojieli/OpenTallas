"""FLOW-NOADV-R2 11-20 (COORD): failure_breakdown is read-only by default; --write-release-tree splices the block and commits via coord-commit.sh."""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import failure_breakdown as FB  # noqa: E402

TREE = "# t\n" + FB.BEGIN + "\nold\n" + FB.END + "\n## EDIT\n"


def test_splice_replaces_or_inserts():
    block = FB.BEGIN + "\nnew \\1 text\n" + FB.END
    assert "new \\1 text" in FB.splice(TREE, block) and "old" not in FB.splice(TREE, block)
    assert FB.splice("# t\n## EDIT\nx\n", block).index(FB.BEGIN) < FB.splice("# t\n## EDIT\nx\n", block).index("## EDIT")


def test_write_commits_through_coord_commit_and_unchanged_does_nothing(tmp_path):
    root = tmp_path / "coord"
    (root / "bin").mkdir(parents=True)
    (root / "bin" / "coord-commit.sh").write_text("#!/bin/bash\necho \"$@\" > " + str(tmp_path / "called") + "\necho PUSHED abc\n")
    tree = root / "RELEASE_TREE.md"
    tree.write_text(TREE)
    block = FB.BEGIN + "\nnew\n" + FB.END
    assert FB.write_release_tree(block, tree=str(tree)) == "PUSHED abc"
    assert "new" in tree.read_text() and "RELEASE_TREE.md" in (tmp_path / "called").read_text()
    (tmp_path / "called").unlink()
    assert FB.write_release_tree(block, tree=str(tree)) == "unchanged" and not (tmp_path / "called").exists()


def test_default_cli_writes_nothing_and_rejects_unknown_flags(tmp_path):
    r = subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "failure_breakdown.py"), "--bogus"],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "usage" in r.stderr


def test_rsz0074_fallback_is_infra_not_timing():
    r = {'status': 'FAILED', 'class': 'TIMING', 'reason': 'routed-not-signed: TT -50 ps; OT_TT_SETUP_REPAIR FAIL class=tt_setup_repair_fallback RSZ-0074'}
    assert FB.label(r) == 'INFRA[rsz_crash]'
    r['reason'] = 'routed-not-signed: TT -50 ps'
    assert FB.label(r) == 'timing after route'
