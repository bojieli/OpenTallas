import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rt_tool_commit as RC   # noqa: E402


def _g(d, *a):
    return subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True, text=True,
                          env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")).stdout.strip()


def _repo(tmp):
    r = tmp / "m"
    _g(tmp, "init", "-q", "-b", "main", str(r))
    shas = []
    for i in range(3):
        (r / "f").write_text(str(i))
        _g(r, "add", "f")
        _g(r, "commit", "-q", "-m", str(i))
        shas.append(_g(r, "rev-parse", "HEAD"))
    return r, shas


def test_check(tmp_path):
    r, (a, b, c) = _repo(tmp_path)
    rt = tmp_path / "rt"
    rt.mkdir()
    (rt / c[:12]).mkdir()
    os.symlink(c[:12], rt / "current")
    assert RC.check(b, b, r, rt)[0] == "OK"                      # equal
    assert RC.check(b, c, r, rt)[0] == "OK"                      # descendant
    v, t = RC.check(b, a, r, rt, what="gate X")                  # older rt: refuse, names both + newest
    assert v == "REFUSE" and "NOT-RUN SETUP" in t and a[:12] in t and b[:12] in t and f"--rt {c[:12]}" in t
    assert RC.check("", a, r, rt)[0] == "SKIP"
    assert RC.check("deadbeefdead", a, r, rt)[0] == "WARN"       # unknown commit fails open
    assert RC.check(b, a, tmp_path / "nomirror", rt)[0] == "WARN"
    os.unlink(rt / "current")
    assert "no qualifying" in RC.check(b, a, r, rt)[1]


def test_tool_commit_of():
    assert RC.tool_commit_of({}, {"dies": {"qc": {"tool_commit": "abc1234"}}}, "qc") == "abc1234"
    assert RC.tool_commit_of({"tool_commit": "s1"}, {}, "qc", "x1") == "x1"
