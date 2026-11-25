"""KV-NOADVANCE 11-25: a BIND-PIN overlay must not mix a pinned old generator with an unpinned caller of its newer API."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def mk(root, rt_src, gen_src):
    d = Path(root) / "tools" / "die_plan"
    d.mkdir(parents=True)
    (d / "reset_tree.py").write_text(rt_src)
    (d / "gen_phys.py").write_text(gen_src)
    return root


def test_pin_refused_when_caller_needs_newer_api(tmp_path):
    new = mk(tmp_path / "new", "def raw_tap_hold(P, t):\n    return 1\nX = 2\n", "import reset_tree as RT\nRT.raw_tap_hold(1, 2)\n")
    old = mk(tmp_path / "old", "def other():\n    return 1\n", "import reset_tree as RT\n")
    assert KW.pin_api_gaps(new, old, ["reset_tree.py"]) == ["gen_phys.py: reset_tree.raw_tap_hold"]
    full = mk(tmp_path / "old2", "def raw_tap_hold(P, t):\n    pass\n", "")
    assert KW.pin_api_gaps(new, full, ["reset_tree.py"]) == []


def test_bind_pins_falls_back_to_whole_bind_rt(tmp_path, monkeypatch):
    new = mk(tmp_path / "new", "def raw_tap_hold(P, t):\n    return 1\n", "import reset_tree as RT\nRT.raw_tap_hold(1, 2)\n")
    old = mk(tmp_path / "old", "def other():\n    return 1\n", "import reset_tree as RT\n")
    h = KW.rt_generator_hashes
    stamp = {"generators": h(old)}
    if not stamp["generators"]:
        return                       # no bind_tool_stamp in this tree
    assert KW.bind_pins(stamp, new, old, "x") is None
