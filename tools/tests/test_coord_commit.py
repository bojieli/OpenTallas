"""FLOW-HEALTH-1 11-15: bin/coord-commit.sh status line, 3 retries, unrelated dirty files.  Scratch repos only, never ~/coord.
    python3 -m pytest -q tools/tests/test_coord_commit.py"""
import os
import subprocess
import tempfile
from pathlib import Path

SCRIPT = os.environ.get("COORD_COMMIT_SCRIPT") or str(Path(__file__).resolve().parents[2] / "bin/coord-commit.sh")


def git(cwd, *a, check=True):
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, check=check).stdout.strip()


def setup():
    d = Path(tempfile.mkdtemp())
    bare = d / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "coord/state", str(bare)], check=True)
    seed = d / "seed"
    subprocess.run(["git", "clone", "-q", str(bare), str(seed)], check=True, capture_output=True)
    for c in (seed,):
        git(c, "config", "user.email", "t@t"); git(c, "config", "user.name", "t")
    (seed / "lanes").mkdir()
    (seed / "lanes/Q.md").write_text("- a\n")
    (seed / "kit_wave.json").write_text("{}\n")
    (seed / "dirty.txt").write_text("x\n")
    git(seed, "add", "-A"); git(seed, "commit", "-q", "-m", "seed"); git(seed, "push", "-q", "origin", "HEAD:coord/state")
    work = d / "coord"
    subprocess.run(["git", "clone", "-q", "-b", "coord/state", str(bare), str(work)], check=True, capture_output=True)
    git(work, "config", "user.email", "t@t"); git(work, "config", "user.name", "t")
    other = d / "other"
    subprocess.run(["git", "clone", "-q", "-b", "coord/state", str(bare), str(other)], check=True, capture_output=True)
    git(other, "config", "user.email", "t@t"); git(other, "config", "user.name", "t")
    return d, bare, work, other


def run(work, msg, *paths):
    env = dict(os.environ, COORD_DIR=str(work), COORD_BRANCH="coord/state", COORD_COMMIT_BACKOFF="0",
               COORD_COMMIT_TLOG=str(work.parent / "tlog"))
    return subprocess.run(["bash", SCRIPT, msg, *paths], capture_output=True, text=True, env=env, timeout=300)


def test_pushed_line_and_origin_holds_it():
    d, bare, work, other = setup()
    (work / "lanes/Q.md").write_text("- a\n- b\n")
    r = run(work, "post b", "lanes/Q.md")
    assert r.returncode == 0, r.stderr
    sha = r.stdout.strip().splitlines()[-1]
    assert sha.startswith("PUSHED ")
    assert git(bare, "rev-parse", "coord/state") == sha.split()[1]
    assert "- b" in git(bare, "show", "coord/state:lanes/Q.md")


def test_unrelated_dirty_and_untracked_files_do_not_block():
    d, bare, work, other = setup()
    (work / "dirty.txt").write_text("hand edit\n")                       # tracked, unrelated, dirty
    (work / "junk.new").write_text("untracked\n")
    (other / "lanes/Q.md").write_text("- a\n- from other\n")
    git(other, "commit", "-q", "-am", "other"); git(other, "push", "-q", "origin", "HEAD:coord/state")
    (work / "lanes/Q.md").write_text("- a\n- mine\n")
    r = run(work, "mine", "lanes/Q.md")
    assert r.returncode == 0 and r.stdout.strip().splitlines()[-1].startswith("PUSHED "), (r.stdout, r.stderr)
    q = git(bare, "show", "coord/state:lanes/Q.md")
    assert "- mine" in q and "- from other" in q
    assert (work / "dirty.txt").read_text() == "hand edit\n" and (work / "junk.new").exists()


def test_dirty_file_that_upstream_also_changed_is_replayed_not_blocked():
    d, bare, work, other = setup()
    (other / "dirty.txt").write_text("upstream change\n")
    git(other, "commit", "-q", "-am", "up"); git(other, "push", "-q", "origin", "HEAD:coord/state")
    (work / "dirty.txt").write_text("my uncommitted hand edit\n")        # the merge would overwrite it: refused in the shared tree
    (work / "lanes/Q.md").write_text("- a\n- mine\n")
    r = run(work, "mine", "lanes/Q.md")
    assert r.returncode == 0 and "PUSHED" in r.stdout, (r.stdout, r.stderr)
    assert "- mine" in git(bare, "show", "coord/state:lanes/Q.md")
    assert (work / "dirty.txt").read_text() == "my uncommitted hand edit\n"       # never touched


def test_unreachable_origin_fails_loudly_nonzero():
    d, bare, work, other = setup()
    git(work, "remote", "set-url", "origin", str(d / "nowhere.git"))
    (work / "lanes/Q.md").write_text("- a\n- c\n")
    r = run(work, "c", "lanes/Q.md")
    assert r.returncode != 0
    assert r.stdout.strip().splitlines()[-1].startswith("FAILED"), (r.stdout, r.stderr)
    assert "FAILED" in r.stderr


def test_missing_path_fails_with_a_message():
    d, bare, work, other = setup()
    r = run(work, "x", "lanes/does-not-exist.md")
    assert r.returncode != 0
    assert "FAILED" in r.stdout


def test_nothing_to_commit_but_origin_has_head_is_pushed_status():
    d, bare, work, other = setup()
    r = run(work, "noop", "lanes/Q.md")
    assert r.returncode == 0 and r.stdout.strip().splitlines()[-1].startswith("PUSHED ")


def test_refuses_a_worktree_that_is_not_on_the_coord_branch():
    """COORD-GUARD 11-19: no commit / push from a worktree that a mistaken checkout moved off coord/state"""
    d, bare, work, other = setup()
    git(work, "checkout", "-q", "-b", "claude/stray")
    (work / "lanes/Q.md").write_text("- a\n- x\n")
    r = run(work, "x", "lanes/Q.md")
    assert r.returncode != 0 and r.stdout.strip().splitlines()[-1].startswith("FAILED") and "not coord/state" in r.stdout
    assert "claude/stray" in r.stdout
    assert git(bare, "rev-parse", "coord/state") == git(work, "rev-parse", "origin/coord/state")           # nothing was pushed
