"""FLOW-NOADV-R3 11-20: a gate resolves rt/current once and keeps that sha when the link moves."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_rowcheck as RC  # noqa: E402
import rt_pin  # noqa: E402


def _rt(tmp_path, *names):
    for n in names:
        (tmp_path / n / "tools" / "die_plan").mkdir(parents=True)
    return tmp_path


def test_pin_resolves_current_to_its_sha_dir_and_survives_a_refresh(tmp_path):
    root = _rt(tmp_path, "aaaa11112222", "bbbb33334444")
    cur = root / "current"
    cur.symlink_to(root / "aaaa11112222")
    env = {}
    assert rt_pin.pin(env, roots=(str(root),)) == str((root / "aaaa11112222").resolve())
    cur.unlink()
    cur.symlink_to(root / "bbbb33334444")                       # five refreshes later
    assert rt_pin.pin(env, roots=(str(root),)) == str((root / "aaaa11112222").resolve())      # the pinned env wins
    assert rt_pin.resolve({}, roots=(str(root),)) == str((root / "bbbb33334444").resolve())   # an unpinned run sees the new one


def test_bind_rowcheck_reference_tree_is_pinned_on_first_use(tmp_path, monkeypatch):
    root = _rt(tmp_path, "aaaa11112222", "bbbb33334444")
    cur = root / "current"
    cur.symlink_to(root / "aaaa11112222")
    monkeypatch.delenv("OT_RT_CURRENT", raising=False)
    first = RC.find_ref_tools(str(cur))
    assert first == (root / "aaaa11112222").resolve()
    cur.unlink()
    cur.symlink_to(root / "bbbb33334444")
    assert RC.find_ref_tools("auto") == first                   # env pinned by the first resolution
    assert os.environ["OT_RT_CURRENT"] == str(first)
