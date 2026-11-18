"""COORD r255b: the wave tick's two slow, read-only parts are memoized / probed concurrently; behaviour is unchanged"""
import subprocess
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as K


def test_unit_active_many_matches_sequential_and_runs_concurrently():
    seen, lock, peak, cur = [], threading.Lock(), [0], [0]

    class AP:
        @staticmethod
        def unit_active(u):
            with lock:
                cur[0] += 1; peak[0] = max(peak[0], cur[0])
            import time; time.sleep(0.05)
            with lock:
                cur[0] -= 1; seen.append(u)
            if u == "boom":
                raise RuntimeError("systemctl broke")
            return u.startswith("on")
    units = ["on1", "off1", "on2", "boom", "on1", "", None]
    got = K.unit_active_many(AP, units)
    assert got == {"on1": True, "off1": False, "on2": True, "boom": False}
    assert sorted(seen) == ["boom", "off1", "on1", "on2"]          # each unit probed once, blanks skipped
    assert peak[0] > 1                                              # probes overlapped
    assert K.unit_active_many(AP, []) == {}


def test_future_lec_snapshot_runs_git_show_and_ast_once_per_commit(tmp_path, monkeypatch):
    calls = []
    real = subprocess.run

    def counting(cmd, *a, **k):
        if cmd[:1] == ["git"] and "show" in cmd:
            calls.append(cmd[-1])
        return real(cmd, *a, **k)
    monkeypatch.setattr(K.subprocess, "run", counting)
    K._SHOW_CACHE.clear(); K._TEMPLATE_CACHE.clear()
    head = real(["git", "-C", str(Path(K.__file__).resolve().parents[1] / "die_plan"), "rev-parse", "HEAD"],
                capture_output=True, text=True).stdout.strip()
    m1 = K.future_lec_snapshot(tmp_path / "a", commit=head)
    n1 = len(calls)
    m2 = K.future_lec_snapshot(tmp_path / "b", commit=head)
    assert m1 == m2 and len(calls) == n1 > 0                        # the second snapshot ran no `git show`
    assert (tmp_path / "a" / "run_kit_template.sh").read_text() == (tmp_path / "b" / "run_kit_template.sh").read_text()
    assert len(K._TEMPLATE_CACHE) == 1
