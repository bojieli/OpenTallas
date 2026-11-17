"""WAVE-FLOW-R2 11-17: TOOLS-LAG = approved die-tool fixes (ruling rNNN on a die_plan / flow path) missing from a die's pinned tools."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tools_lag as TL


def git(repo, *a, env=None):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True)


def commit(repo, rel, text, msg):
    f = Path(repo) / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def make(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    pin = commit(r, "tools/die_plan/a.py", "1", "base")
    commit(r, "tools/die_plan/a.py", "2", "S81 bind: fix (COORD r535)")
    commit(r, "docs/x.md", "x", "docs only (COORD r536)")                        # ruling but no die tool path: not listed
    commit(r, "tools/die_plan/b.py", "b", "plain refactor without a ruling")      # counted as a commit, not as a ruling
    commit(r, "physical/common_flow/c.tcl", "c", "flow fix\n\nRULING r554 approved")
    return r / ".git", pin


def test_lag_lists_rulings_on_die_tool_paths(tmp_path):
    repo, pin = make(tmp_path)
    res = TL.lag(repo, pin)
    assert res["n_commits"] == 3 and res["missing"] == ["r535", "r554"]
    assert TL.line("kv", res) == "TOOLS-LAG kv 3 commits / missing r535 r554"
    assert TL.lag(repo, "HEAD")["n_commits"] == 0 and TL.line("kv", TL.lag(repo, "HEAD")).endswith("0 commits / missing none")


def test_pin_resolution_and_unmeasured(tmp_path):
    assert TL.pin_of({"tools_sha": "abc1234", "src_sha": "main@ffff"}) == "abc1234"
    assert TL.pin_of({"src_sha": "main@eb1e73448bd0"}) == "eb1e73448bd0"
    m = tmp_path / "tree"
    m.mkdir()
    (m / ".src-manifest.json").write_text('{"main_sha": "1234567abcde"}')
    assert TL.pin_of({"src": str(m), "src_sha": "main@ffff"}) == "1234567abcde"
    assert TL.line("x", TL.lag("/nonexistent", "")).startswith("TOOLS-LAG x unmeasured")
    res = TL.measure({"dies": {"a": {"enabled": True, "src_sha": "main@deadbee"}, "b": {"enabled": False}}}, repo=tmp_path / "nope")
    assert list(res) == ["a"] and res["a"]["n_commits"] is None
