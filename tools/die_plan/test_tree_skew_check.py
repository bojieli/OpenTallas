import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import tree_skew_check as T


def _tree(tmp, files):
    d = Path(tmp) / "tools" / "die_plan"
    d.mkdir(parents=True)
    for n, t in files.items():
        (d / n).write_text(t)
    return str(tmp)


def test_current_tree_is_consistent():
    assert T.check(str(Path(__file__).resolve().parents[2])) == []


def test_generator_without_checker_is_flagged(tmp_path):
    t = _tree(tmp_path, {"gen_phys.py": "def tap_offset_lines(): pass\n", "sdc_lint.py": "x = 1\n",
                         "face_guard.py": "def guard(ring_reset=False): pass\n", "hard_landing.py": "F.guard(x)\n"})
    msgs = T.check(t)
    assert len(msgs) == 2 and any("tap_offset_ps" in m for m in msgs) and any("ring_reset" in m for m in msgs)
    assert T.main([t]) == 1


def test_matched_pair_passes(tmp_path):
    t = _tree(tmp_path, {"gen_phys.py": "def tap_offset_lines(): pass\n", "sdc_lint.py": "tap_offset_ps=None\n"})
    assert T.check(t) == [] and T.main([t]) == 0
