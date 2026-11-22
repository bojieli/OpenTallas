"""WAVE-FLOW-R2 11-17 (COORD FABLE-FLOW-1700 items 1 and 2): TOOLS-LAG maps rulings to shas through COORD.md `COORD APPROVED: <branch> @<sha>` lines and tests ancestry
against the die tree tools base (no commit-message parsing); tree_has answers the same question for hold release terms."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools_lag as TL


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True, text=True).stdout.strip()


def commit(repo, rel, text, msg):
    f = Path(repo) / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


def merge_branch(repo, name, rel, text):
    """a branch with one commit merged into main with a merge commit -> (branch tip sha, merge sha)"""
    git(repo, "checkout", "-q", "-b", name)
    tip = commit(repo, rel, text, f"branch {name}")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "-m", f"Merge {name} @{tip[:11]}", name)
    return tip, git(repo, "rev-parse", "HEAD")


def make(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    commit(r, "tools/base.py", "1", "base")
    t1, _ = merge_branch(r, "fix-a", "tools/die_plan/a.py", "a")
    pin = git(r, "rev-parse", "HEAD")                                   # the die tree tools base: after fix-a
    t2, _ = merge_branch(r, "fix-b", "tools/closure_loop/b.py", "b")  # r623-like: not under tools/die_plan
    t3, _ = merge_branch(r, "fix-doc", "docs/x.md", "d")                # a ruling that touches no tool path
    git(r, "checkout", "-q", "-b", "unmerged")
    t4 = commit(r, "tools/die_plan/c.py", "c", "not merged yet")
    git(r, "checkout", "-q", "main")
    return r / ".git", pin, dict(a=t1, b=t2, doc=t3, unmerged=t4)


COORD = """- 2026-11-17 15:00 PST RULING r601 [COORD -> X] fix a (message says nothing useful)
  COORD APPROVED: claude/fix-a @{a}
- 2026-11-17 15:10 PST RULING r623 [COORD -> Y] job env
  COORD APPROVED: claude/fix-b @{b}
- 2026-11-17 15:20 PST RULING r630 [COORD -> Z] doc only\\nCOORD APPROVED: claude/fix-doc @{doc}
- 2026-11-17 15:30 PST RULING r640 [COORD -> W] not merged
  COORD APPROVED: claude/unmerged @{unmerged}
- 2026-11-17 15:40 PST RULING r650 [COORD -> W] design ruling, no approved branch
"""


def test_ruling_shas_associates_approved_lines_with_the_nearest_ruling():
    shas = dict(a="a" * 40, b="b" * 40, doc="c" * 40, unmerged="d" * 40)
    m = TL.ruling_shas(COORD.format(**shas))
    assert m == {"r601": ["a" * 40], "r623": ["b" * 40], "r630": ["c" * 40], "r640": ["d" * 40]}          # inline (literal \\n) and own-line forms; r650 has none
    assert TL.ruling_shas("COORD APPROVED: x @" + "e" * 40) == {}                                          # an approval before any ruling belongs to none


def test_lag_by_ancestry_not_messages(tmp_path):
    repo, pin, t = make(tmp_path)
    rulings = TL.ruling_shas(COORD.format(**t))
    TL.clear_caches()
    res = TL.lag(repo, pin, "main", rulings=rulings)
    assert res["missing"] == ["r623"]                       # r601 is in the pin; r630 touches no tool path; r640 is not merged; r623 is merged after the pin
    assert res["n_commits"] >= 1 and TL.line("kv", res).endswith("missing r623")
    for r, want in (("r601", "has"), ("r623", "missing"), ("r630", "not_tool"), ("r640", "not_merged")):
        assert TL.ruling_state(repo, pin, rulings[r])[0] == want, r
    assert TL.lag(repo, "HEAD", "main", rulings=rulings)["missing"] == []                  # a tree at main lacks nothing


def test_tree_has_ruling_and_sha(tmp_path):
    repo, pin, t = make(tmp_path)
    rulings = TL.ruling_shas(COORD.format(**t))
    TL._HAS_CACHE.clear()
    TL.clear_caches()
    assert TL.tree_has(repo, pin, "r601", rulings) is True
    assert TL.tree_has(repo, pin, "r623", rulings) is False                                 # merged after the pin: the tree does not have it
    assert TL.tree_has(repo, "main", "r623", rulings) is True
    assert TL.tree_has(repo, pin, "r640", rulings) is False and TL.tree_has(repo, pin, "r999", rulings) is False
    assert TL.tree_has(repo, pin, t["a"][:12]) is True and TL.tree_has(repo, pin, t["b"]) is False        # tree_has_sha form
    assert TL.tree_has(repo, pin, "not-a-token", rulings) is False


def test_pin_resolution_and_unmeasured(tmp_path):
    assert TL.pin_of({"tools_sha": "abc1234", "src_sha": "main@ffff"}) == "abc1234"
    assert TL.pin_of({"src_sha": "main@eb1e73448bd0"}) == "eb1e73448bd0"
    m = tmp_path / "tree"
    m.mkdir()
    (m / ".src-manifest.json").write_text('{"main_sha": "1234567abcde"}')
    assert TL.pin_of({"src": str(m), "src_sha": "main@ffff"}) == "1234567abcde"
    assert TL.line("x", TL.lag("/nonexistent", "", rulings={})).startswith("TOOLS-LAG x unmeasured")
    res = TL.measure({"dies": {"a": {"enabled": True, "src_sha": "main@deadbee"}, "b": {"enabled": False}}}, repo=tmp_path / "nope", rulings={})
    assert list(res) == ["a"] and res["a"]["n_commits"] is None



def test_measure_uses_launch_rt_pin_over_stale_tree_pin(monkeypatch):
    """TOOLS-LAG-RT-1122: a die whose launches compose rt/<sha> is measured at that sha, not at its stale tools_sha"""
    import tools_lag as TL2
    seen = {}
    monkeypatch.setattr(TL2, "lag", lambda repo, pin, main_ref="main", paths=None, rulings=None: seen.setdefault("p", []).append(pin) or dict(pin=pin, n_commits=0, missing=[], shas={}))
    cfg = {"dies": {"s81": {"enabled": True, "tools_sha": "a9ed808a98d5"}, "head": {"enabled": True, "tools_sha": "30b1f11ad5f7"}}}
    out = TL2.measure(cfg, rulings={}, pins={"s81": "4396e129eff7"})
    assert seen["p"] == ["4396e129eff7", "30b1f11ad5f7"] and out["s81"]["pin_src"] == "rt" and out["head"]["pin_src"] == "tree"
