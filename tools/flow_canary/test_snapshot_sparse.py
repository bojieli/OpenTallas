"""FLOW-16 10-31: a job with GIT_DIR=<snapshot>/.git and macro files in its cwd must not dirty the canary snapshot.
    python3 -m pytest -q tools/flow_canary/test_snapshot_sparse.py"""
import importlib.util
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("flow_canary_trigger", HERE / "trigger.py")
trigger = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(trigger)


def _git(cwd, *a, **env):
    return subprocess.run(["git", *a], cwd=cwd, text=True, capture_output=True, check=True, env={**os.environ, **env})


def _snapshot(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "a@b")
    _git(repo, "config", "user.name", "a")
    (repo / "tools").mkdir()
    (repo / "tools" / "t").write_text("1")
    (repo / "physical" / "m").mkdir(parents=True)
    (repo / "physical" / "m" / "x.lef").write_text("2")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "x")
    dest = tmp_path / "sources" / "snap"
    _git(repo, "worktree", "add", "-q", "--no-checkout", "--detach", str(dest), "HEAD")
    _git(dest, "sparse-checkout", "set", "--no-cone", "/*", "!/physical/")
    _git(dest, "checkout", "-q", "--detach", "HEAD")
    return dest


def _job(tmp_path, dest):
    src = tmp_path / "run" / "src" / "physical" / "m"
    src.mkdir(parents=True)
    (src / "x.lef").write_text("2")
    _git(tmp_path / "run" / "src", "status", "--porcelain", GIT_DIR=str(dest / ".git"))


def test_job_git_dir_does_not_dirty_snapshot(tmp_path):
    dest = _snapshot(tmp_path)
    trigger.hold_sparse(dest)
    _job(tmp_path, dest)
    assert _git(dest, "status", "--porcelain").stdout == ""


def test_flipped_snapshot_is_repaired(tmp_path):
    dest = _snapshot(tmp_path)
    _job(tmp_path, dest)
    assert " D physical/m/x.lef" in _git(dest, "status", "--porcelain").stdout   # the failure this fixes
    trigger.hold_sparse(dest)
    assert _git(dest, "status", "--porcelain").stdout == ""
