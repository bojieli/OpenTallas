"""TOOLSTALE-GATE-RT-1123 (COORD 16:3x): a pinned $OT_RT_CURRENT (the rt the gate / ot-run unit started on) is the TOOLSTALE reference for the
whole run, even after rt/current moved; a pruned pin is found under another scratch root by its sha, else no comparison + WARN."""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_rowcheck as RC  # noqa: E402


def _rt(root, sha, body="x = 1\n", age=0):
    d = root / sha / "tools" / "die_plan"
    d.mkdir(parents=True)
    f = d / "a.py"
    f.write_text(body)
    t = time.time() - age
    os.utime(f, (t, t))
    return root / sha


def test_pinned_env_wins_over_a_moved_rt_current(tmp_path, monkeypatch):
    root = tmp_path / "rt"
    old = _rt(root, "aaaa11112222", "x = 1\n", age=7200)
    _rt(root, "bbbb33334444", "x = 22\n")                  # newer tools, written after the gate started
    (root / "current").symlink_to(root / "bbbb33334444")   # rt/current moved during the gate
    tree = tmp_path / "tree"
    (tree / "tools" / "die_plan").mkdir(parents=True)
    (tree / "tools" / "die_plan" / "a.py").write_text("x = 1\n")
    t = time.time() - 3600
    os.utime(tree / "tools" / "die_plan" / "a.py", (t, t))
    monkeypatch.delenv("OT_RT_CURRENT", raising=False)
    monkeypatch.setenv("OT_TOOLSTALE_RT", str(old))                  # ot-run pinned it at unit start
    assert RC.find_ref_tools("auto", rt_roots=(str(root),)) == old.resolve()
    assert "OT_RT_CURRENT" not in os.environ                          # the global tool-root variable is left alone
    monkeypatch.setattr(RC, "RT_ROOTS", (str(root),))
    assert RC.check_toolstale(str(tree), "auto") == []     # same bytes as the pinned rt: no TOOLSTALE
    monkeypatch.delenv("OT_TOOLSTALE_RT")
    out = RC.check_toolstale(str(tree), "auto")            # unpinned: compares against the new rt and names its sha
    assert out and out[0].startswith("FAIL TOOLSTALE") and "ref rt bbbb33334444" in out[0]


def test_pruned_pin_is_found_by_sha_under_another_root(tmp_path, monkeypatch):
    other = tmp_path / "s3" / "rt"
    kept = _rt(other, "aaaa11112222")
    _rt(tmp_path / "s2" / "rt", "bbbb33334444")
    (tmp_path / "s2" / "rt" / "current").symlink_to(tmp_path / "s2" / "rt" / "bbbb33334444")
    monkeypatch.setenv("OT_TOOLSTALE_RT", str(tmp_path / "s2" / "rt" / "aaaa11112222"))     # pruned on this root
    roots = (str(tmp_path / "s2" / "rt"), str(other))
    assert RC.find_ref_tools("auto", rt_roots=roots) == kept.resolve()


def test_pruned_pin_gone_everywhere_gives_no_reference_and_warns(tmp_path, monkeypatch):
    root = tmp_path / "rt"
    _rt(root, "bbbb33334444")
    (root / "current").symlink_to(root / "bbbb33334444")
    monkeypatch.delenv("OT_RT_CURRENT", raising=False)
    monkeypatch.setenv("OT_TOOLSTALE_RT", str(root / "aaaa11112222"))
    monkeypatch.setattr(RC, "RT_ROOTS", (str(root),))
    assert RC.find_ref_tools("auto") is None
    out = RC.check_toolstale(str(tmp_path), "auto")
    assert len(out) == 1 and out[0].startswith("WARN TOOLSTALE pinned $OT_TOOLSTALE_RT=")
    assert "OT_RT_CURRENT" not in os.environ                          # never re-pinned to the later rt


def test_toolstale_pin_wins_over_a_global_rt_pin(tmp_path, monkeypatch):
    root = tmp_path / "rt"
    a, b = _rt(root, "aaaa11112222"), _rt(root, "bbbb33334444")
    monkeypatch.setenv("OT_RT_CURRENT", str(b))
    monkeypatch.setenv("OT_TOOLSTALE_RT", str(a))
    assert RC.find_ref_tools("auto", rt_roots=(str(root),)) == a.resolve()
    assert os.environ["OT_RT_CURRENT"] == str(b)
