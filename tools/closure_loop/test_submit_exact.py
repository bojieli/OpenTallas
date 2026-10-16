"""submit_exact: spec follows the commit; kit/consumed paths come from the route command (ROOT 2026-10-15)."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import submit_exact as S  # noqa: E402

SPEC = {"name": "s81net_x-n4-7f5182219", "block": "x", "ref_tile": True,
        "source": {"commit": "7f5182219", "extra_paths": ["rtl/a"]}, "sources": ["rtl/b.sv"],
        "stages": {"route": {"cmd": "bash tools/ref_tile/ref_route.sh physical/ref_tile/x/kit.env"}}}


def test_move_spec_renames_suffix():
    s = S.move_spec(SPEC, "abcdef0123456789")
    assert s["name"] == "s81net_x-n4-abcdef012" and s["source"]["commit"] == "abcdef012"
    assert SPEC["source"]["commit"] == "7f5182219"


def test_consumed_paths():
    assert S.kit_of(SPEC) == "physical/ref_tile/x"
    assert S.consumed_paths(SPEC) == ["physical/ref_tile/x", "rtl/b.sv", "rtl/a"]


def test_dirty_detects_uncommitted_and_moved(tmp_path):
    def g(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)
    g("init", "-q"); g("config", "user.email", "t@t"); g("config", "user.name", "t")
    (tmp_path / "k").mkdir(); (tmp_path / "k" / "f").write_text("1")
    g("add", "k"); g("commit", "-qm", "a")
    c1 = S.git(tmp_path, "rev-parse", "HEAD")
    assert S.dirty(tmp_path, c1, ["k"]) == ([], [])
    (tmp_path / "k" / "f").write_text("2")
    assert S.dirty(tmp_path, c1, ["k"])[0] == ["k/f"]
    g("commit", "-qam", "b")
    assert S.dirty(tmp_path, c1, ["k"]) == ([], ["k/f"])
