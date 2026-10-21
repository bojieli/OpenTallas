"""ROOT-0615 10-18: a branch commit that copies a file from main (git checkout origin/main -- f) is neutral in rule_span
when main's own commits between its pre and post blobs are classified; an own edit on the branch stays unclassified."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import helper_overlay as HO  # noqa: E402


def g(repo, *a):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True,
                          capture_output=True, text=True).stdout.strip()


def blob(repo, rev):
    return g(repo, "rev-parse", f"{rev}:f.py")


def test_copy_of_main(tmp_path):
    r = tmp_path
    g(r, "init", "-q", "-b", "main")
    (r / "f.py").write_text("A = 1\n")
    g(r, "add", "f.py"); g(r, "commit", "-qm", "base")
    g(r, "checkout", "-qb", "br"); (r / "g.txt").write_text("x"); g(r, "add", "g.txt"); g(r, "commit", "-qm", "gate")
    old = blob(r, "HEAD")
    g(r, "checkout", "-q", "main"); (r / "f.py").write_text("A = 2\n"); g(r, "add", "f.py")
    g(r, "commit", "-qm", "relax\n\nGate-Rule: relaxing")
    g(r, "checkout", "-q", "br"); g(r, "checkout", "main", "--", "f.py"); g(r, "commit", "-qm", "take tools from main")
    ok, rows, why = HO.rule_span(r, "f.py", old, blob(r, "HEAD"), ["main", "br"])
    assert ok, why
    assert {x["kind"] for x in rows} == {"neutral", "relaxing"}
    (r / "f.py").write_text("A = 3\n"); g(r, "add", "f.py"); g(r, "commit", "-qm", "own edit")
    ok, rows, why = HO.rule_span(r, "f.py", old, blob(r, "HEAD"), ["main", "br"])
    assert not ok and "unclassified" in why
