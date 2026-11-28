"""P-LAUNCH-STAMP-RT-ONLY: two trees on one rt get distinct launch dirs; a stamp for A is not accepted for B; rt+tree reuses its dir."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import publish_gate as PG  # noqa: E402

COMPOSER = Path(__file__).resolve().parent / "rt_launch_tree.sh"


def _mk(tmp_path):
    rt = tmp_path / "rt" / "b71c5218e0b5"
    (rt / "tools").mkdir(parents=True)
    (rt / "tools" / "t.py").write_text("x\n")
    trees = {}
    for n in ("A", "B"):
        t = tmp_path / ("tree" + n)
        (t / "tools").mkdir(parents=True)
        (t / "physical").mkdir()
        (t / "marker").write_text(n)
        trees[n] = t
    return rt, trees


def _compose(tree, rt, dest):
    return subprocess.run(["bash", str(COMPOSER), str(tree), str(rt), str(dest)], capture_output=True, text=True)


def test_dir_keyed_by_rt_and_tree(tmp_path):
    rt, t = _mk(tmp_path)
    work = tmp_path / "work"
    a1, a2 = PG.pre_launch_dir(work, rt, t["A"]), PG.pre_launch_dir(work, rt, t["A"])
    b = PG.pre_launch_dir(work, rt, t["B"])
    assert a1 == a2 and a1 != b
    assert Path(a1).name.startswith("pre-b71c5218e0b5-")


def test_stamp_for_a_not_accepted_for_b(tmp_path):
    rt, t = _mk(tmp_path)
    work = tmp_path / "work"
    da, db = PG.pre_launch_dir(work, rt, t["A"]), PG.pre_launch_dir(work, rt, t["B"])
    assert _compose(t["A"], rt, da).returncode == 0
    assert _compose(t["B"], rt, db).returncode == 0          # distinct dir: no collision
    assert _compose(t["A"], rt, da).returncode == 0          # same rt+tree: reuse
    r = _compose(t["B"], rt, da)                              # A's stamp must not serve B
    assert r.returncode == 97 and "incompatible launch stamp" in r.stderr
