"""FLOW-HEALTH-1 11-19 (COORD incident): the hub-coord worktree stays on coord/state.  Scratch repos only; every git call has an explicit cwd that must exist."""
import os
import subprocess
from pathlib import Path

GUARD = Path(__file__).resolve().parent / "coord-branch-guard"


def git(cwd, *a, env=None, check=True):
    cwd = Path(cwd)
    assert cwd.is_dir(), cwd                                    # never fall back to another directory
    e = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t", **(env or {}))
    for k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        e.pop(k, None)
    r = subprocess.run(["git", *a], cwd=str(cwd), capture_output=True, text=True, env=e)
    if check:
        assert r.returncode == 0, (a, r.stdout, r.stderr)
    return r


def setup(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    git(repo, "config", "extensions.worktreeConfig", "true")
    (repo / "m1.txt").write_text("main\n")
    (repo / "mdir").mkdir()
    (repo / "mdir/m2.txt").write_text("main2\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "main")
    git(repo, "checkout", "-q", "-b", "coord/state")
    git(repo, "rm", "-q", "-r", "m1.txt", "mdir")
    (repo / "lanes").mkdir()
    for i in range(5):
        (repo / f"lanes/c{i}.md").write_text(f"coord {i}\n")
    (repo / "bin").mkdir()
    (repo / "bin/coord-commit.sh").write_text("#!/bin/bash\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "coord")
    git(repo, "checkout", "-q", "main")
    hub = tmp_path / "hub-coord"
    git(repo, "worktree", "add", "-q", str(hub), "coord/state")
    home = tmp_path / "home"
    home.mkdir()
    r = subprocess.run(["bash", str(GUARD / "install.sh"), str(hub)], capture_output=True, text=True, env=dict(os.environ, HOME=str(home)))
    assert r.returncode == 0, r.stderr
    return repo, hub, home


def clean_on_coord_state(hub):
    assert git(hub, "symbolic-ref", "--short", "HEAD").stdout.strip() == "coord/state"
    assert git(hub, "status", "--porcelain").stdout == ""
    assert all((hub / f"lanes/c{i}.md").exists() for i in range(5)) and (hub / "bin/coord-commit.sh").exists()
    assert not (hub / "m1.txt").exists() and not (hub / "mdir").exists()          # main-only files are gone again


def test_the_incident_command_is_undone(tmp_path):
    repo, hub, _ = setup(tmp_path)
    r = git(hub, "checkout", "-q", "-f", "-B", "claude/flow-0555", "main", check=False)
    assert "COORD-GUARD" in r.stderr
    clean_on_coord_state(hub)


def test_switch_to_an_existing_branch_and_detached_checkout_are_undone(tmp_path):
    repo, hub, _ = setup(tmp_path)
    git(repo, "branch", "lane-x", "main")
    git(hub, "checkout", "-q", "lane-x", check=False)
    clean_on_coord_state(hub)
    git(hub, "checkout", "-q", "--detach", "main", check=False)
    clean_on_coord_state(hub)
    git(hub, "switch", "-q", "main", check=False)
    clean_on_coord_state(hub)


def test_normal_coord_commit_operations_still_work(tmp_path):
    repo, hub, _ = setup(tmp_path)
    (hub / "lanes/c0.md").write_text("changed\n")
    git(hub, "checkout", "--", "lanes/c0.md")                                        # file checkout (flag 0) is not a branch checkout
    assert (hub / "lanes/c0.md").read_text() == "coord 0\n"
    (hub / "lanes/new.md").write_text("post\n")
    git(hub, "add", "lanes/new.md")
    git(hub, "commit", "-qm", "post")                                                # moves refs/heads/coord/state: allowed
    git(repo, "clone", "-q", str(repo), str(tmp_path / "other"))
    git(hub, "remote", "add", "origin", str(repo))
    git(hub, "fetch", "-q", "origin")
    git(hub, "merge", "-q", "--no-edit", "origin/coord/state", check=False)
    tree = git(hub, "write-tree").stdout.strip()
    git(hub, "commit-tree", tree, "-p", "HEAD", "-m", "private index style commit")
    clean_on_coord_state(hub)


def test_other_worktrees_and_the_main_repo_are_not_guarded(tmp_path):
    repo, hub, _ = setup(tmp_path)
    lane = tmp_path / "lane"
    git(repo, "worktree", "add", "-q", "-b", "lane-b", str(lane), "main")
    git(lane, "checkout", "-q", "-B", "lane-c", "main")
    assert git(lane, "symbolic-ref", "--short", "HEAD").stdout.strip() == "lane-c"
    git(repo, "branch", "free-branch")


def test_off_switch_for_maintenance(tmp_path):
    repo, hub, _ = setup(tmp_path)
    git(hub, "checkout", "-q", "-B", "maint", "main", env={"COORD_GUARD_OFF": "1"})
    assert git(hub, "symbolic-ref", "--short", "HEAD").stdout.strip() == "maint"


def test_installer_refuses_a_plain_checkout_and_keeps_an_existing_other_hookspath(tmp_path):
    repo = tmp_path / "plain"
    repo.mkdir()
    git(repo, "init", "-q")
    r = subprocess.run(["bash", str(GUARD / "install.sh"), str(repo)], capture_output=True, text=True, env=dict(os.environ, HOME=str(tmp_path)))
    assert r.returncode != 0 and "not a linked worktree" in r.stderr
    (tmp_path / "second").mkdir()
    _, hub, home = setup(tmp_path / "second")
    gd = Path(hub / ".git").read_text().split("gitdir: ")[1].strip()
    cfg = Path(gd) / "config.worktree"
    assert "hooksPath" in cfg.read_text()
    cfg.write_text("[core]\n\thooksPath = /somewhere/else\n")
    r = subprocess.run(["bash", str(GUARD / "install.sh"), str(hub)], capture_output=True, text=True, env=dict(os.environ, HOME=str(home)))
    assert r.returncode != 0 and "already sets another core.hooksPath" in r.stderr
    assert "/somewhere/else" in cfg.read_text()


def test_pre_push_chains_to_the_shared_hook(tmp_path):
    repo, hub, home = setup(tmp_path)
    shared = repo / ".git/hooks/pre-push"
    shared.write_text("#!/bin/sh\necho SHARED-PRE-PUSH-RAN >&2\nexit 1\n")
    shared.chmod(0o755)
    git(hub, "remote", "add", "o2", str(tmp_path / "bare"))
    git(tmp_path, "init", "-q", "--bare", str(tmp_path / "bare"))
    r = git(hub, "push", "o2", "coord/state", check=False)
    assert r.returncode != 0 and "SHARED-PRE-PUSH-RAN" in r.stderr
