"""ROOT-RULETAG 10-19: gate_rule_guard refuses a push to main that brings an unclassified commit on a gate / daemon-overlay
helper (the 03c544ca1 / b7918e979 / view_export.py class), and the root_pre_push.sh hook enforces it."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gate_rule_guard as G  # noqa: E402

ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True, env=ENV).stdout.strip()


def commit(repo, files, msg):
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        git(repo, "add", rel)
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


def repo(tmp):
    r = tmp / "r"
    r.mkdir(parents=True)
    git(r, "init", "-q", "-b", "main")
    for f in ("helper_overlay.py", "gate_rule_guard.py", "root_pre_push.sh"):
        (r / "tools/closure_loop").mkdir(parents=True, exist_ok=True)
        shutil.copy(HERE / f, r / "tools/closure_loop" / f)
        git(r, "add", f"tools/closure_loop/{f}")
    commit(r, {"tools/closure_loop/ck_insertion.py": "X = 1\n", "physical/common_flow/a.tcl": "set a 1\n"},
           "base\n\nGate-Rule: neutral")
    base = git(r, "rev-parse", "HEAD")
    commit(r, {"tools/closure_loop/ck_insertion.py": "X = 2\n"}, "main v2\n\nGate-Rule: neutral")
    git(r, "branch", "base", "HEAD")
    return r, base


def run(r, tip="HEAD"):
    return G.check(str(r), "base", tip)


def test_unclassified_helper_commit_refused(tmp_path):
    r, _ = repo(tmp_path)
    c = commit(r, {"tools/closure_loop/ck_insertion.py": "X = 3\n"}, "tweak ck")
    ok, rows = run(r)
    assert not ok and rows[0]["commit"] == c and rows[0]["path"] == "tools/closure_loop/ck_insertion.py"
    assert G.main(["--repo", str(r), "--base", "base"]) == 1


def test_common_flow_and_view_export_guarded(tmp_path):
    r, _ = repo(tmp_path)
    commit(r, {"physical/common_flow/a.tcl": "set a 2\n"}, "flow")
    assert not run(r)[0]
    r2, _ = repo(tmp_path / "x")
    commit(r2, {"tools/tt_views/view_export.py": "Y = 1\n"}, "export")
    assert not run(r2)[0]


def test_trailer_passes(tmp_path):
    r, _ = repo(tmp_path)
    commit(r, {"tools/closure_loop/ck_insertion.py": "X = 3\n"}, "tweak ck\n\nGate-Rule: tightening requires=foo")
    assert run(r)[0]


def test_rule_commits_entry_in_same_push_passes(tmp_path):
    r, _ = repo(tmp_path)
    c = commit(r, {"tools/closure_loop/ck_insertion.py": "X = 3\n"}, "tweak ck")
    ho = (r / "tools/closure_loop/helper_overlay.py").read_text()
    ho = ho.replace("RULE_COMMITS = {\n", f'RULE_COMMITS = {{\n    "{c}": dict(kind="neutral", rule="t", what="t"),\n', 1)
    commit(r, {"tools/closure_loop/helper_overlay.py": ho}, "classify\n\nGate-Rule: neutral")
    ok, rows = run(r)
    assert ok, rows


def test_comment_only_tests_and_copy_of_main_pass(tmp_path):
    r, _ = repo(tmp_path)
    commit(r, {"tools/closure_loop/ck_insertion.py": "# note\nX = 2\n"}, "comment")
    commit(r, {"tools/closure_loop/test_x.py": "def test(): pass\n", "tools/ref_tile/README.md": "x\n"}, "tests")
    commit(r, {"tools/closure_loop/ck_insertion.py": "X = 1\n"}, "take tool from an older main revision")
    ok, rows = run(r)
    assert ok, rows


def test_merges_skipped_but_their_commits_checked(tmp_path):
    r, _ = repo(tmp_path)
    git(r, "checkout", "-q", "-b", "lane")
    commit(r, {"tools/ref_tile/gen.py": "Z = 1\n"}, "lane tool")
    git(r, "checkout", "-q", "main")
    commit(r, {"other.txt": "o\n"}, "other")
    git(r, "merge", "-q", "--no-ff", "--no-edit", "lane")
    ok, rows = run(r)
    assert not ok and rows[0]["path"] == "tools/ref_tile/gen.py"


def test_pre_push_hook(tmp_path):
    r, _ = repo(tmp_path)
    base = git(r, "rev-parse", "base")
    bad = commit(r, {"tools/closure_loop/ck_insertion.py": "X = 3\n"}, "tweak ck")
    hook = r / "tools/closure_loop/root_pre_push.sh"
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "git-lfs").write_text("#!/bin/sh\ncat >/dev/null\nexit 0\n")
    (fake / "git-lfs").chmod(0o755)
    env = dict(ENV, PATH=f"{fake}:{os.environ['PATH']}")
    line = f"refs/heads/main {bad} refs/heads/main {base}\n"
    p = subprocess.run(["sh", str(hook), "origin", "u"], input=line, cwd=r, env=env, capture_output=True, text=True)
    assert p.returncode == 1 and "REFUSED" in p.stderr, p.stderr
    # pushes to other branches are not checked
    p = subprocess.run(["sh", str(hook), "origin", "u"], input=line.replace("refs/heads/main", "refs/heads/lane", 2)
                       .replace(f"{bad} refs/heads/lane", f"{bad} refs/heads/lane"), cwd=r, env=env, capture_output=True,
                       text=True)
    assert p.returncode == 0, p.stderr
    good = commit(r, {"tools/closure_loop/ck_insertion.py": "X = 4\n"}, "x\n\nGate-Rule: neutral")
    git(r, "reset", "-q", "--hard", "base")
    good = commit(r, {"tools/closure_loop/ck_insertion.py": "X = 4\n"}, "x\n\nGate-Rule: neutral")
    p = subprocess.run(["sh", str(hook), "origin", "u"], input=f"refs/heads/main {good} refs/heads/main {base}\n", cwd=r,
                       env=env, capture_output=True, text=True)
    assert p.returncode == 0 and "PASS" in p.stderr, p.stderr
    p = subprocess.run(["sh", str(hook), "origin", "u"], input=line, cwd=r, env=dict(env, OT_GATE_RULE_GUARD="off"),
                       capture_output=True, text=True)
    assert p.returncode == 0
