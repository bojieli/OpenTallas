"""count_hourly: a row only from a fresh scan, one row per hour per count, a gap stays a gap."""
import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_hourly as CH

NOW = time.mktime(time.strptime("2026-11-04 07:05", "%Y-%m-%d %H:%M"))


def cache(gen):
    d = lambda n: {str(i): ["r"] for i in range(n)}
    return {"generated": gen, "plans": {
        "a": {"die": "s81", "signed_designs": d(37), "signed_types": {}},
        "b": {"die": "s81_head", "signed_designs": d(4), "signed_types": d(5)},
        "c": {"die": "qwen_compute", "signed_designs": d(12)},
        "e": {"die": "qwen_kvsys", "signed_designs": d(20)},
        "f": {"die": "hbm", "signed_designs": d(12)}}}


@pytest.fixture
def env(tmp_path, monkeypatch):
    (tmp_path / "lanes").mkdir()
    monkeypatch.setattr(CH, "COORD", tmp_path)
    monkeypatch.setattr(CH, "CACHE", tmp_path / "cache.json")
    monkeypatch.setattr(CH, "STATE", tmp_path / "state")
    return tmp_path


def rows(env):
    p = env / CH.RATE
    return p.read_text().splitlines() if p.exists() else []


def put(env, gen):
    (env / "cache.json").write_text(json.dumps(cache(gen)))


def test_row_shape_matches_the_hand_rows():
    assert CH.rate_row(cache(0), "2026-11-04 05:36") == "2026-11-04 05:36 90 s81=37 head=4+5t qc=12 kv=20 hbm=12 auto"


def test_stale_cache_is_scanned_then_row_committed(env):
    put(env, NOW - 3600)
    calls = []

    def scan():
        calls.append(1)
        put(env, NOW - 1)
        return 0
    assert CH.run(NOW, scan, lambda: calls.append(2) or 0) == 0
    assert calls == [1, 2] and rows(env) == ["2026-11-04 07:05 90 s81=37 head=4+5t qc=12 kv=20 hbm=12 auto"]


def test_fresh_cache_no_second_scan(env):
    put(env, NOW - 600)
    assert CH.run(NOW, lambda: pytest.fail("scanned"), lambda: 0) == 0
    assert len(rows(env)) == 1


@pytest.mark.parametrize("rc,refresh", [(1, False), (124, False), (0, False)])
def test_failed_or_silent_scan_leaves_a_true_gap(env, rc, refresh):
    put(env, NOW - 3600)
    assert CH.run(NOW, lambda: rc, lambda: pytest.fail("committed")) == 1
    assert rows(env) == []


def test_same_counts_in_the_hour_is_not_a_new_row(env):
    put(env, NOW - 60)
    (env / CH.RATE).write_text("2026-11-04 07:01 90 s81=37 head=4+5t qc=12 kv=20 hbm=12\n")
    assert CH.run(NOW, None, lambda: pytest.fail("committed")) == 0
    assert len(rows(env)) == 1


def test_changed_counts_in_the_hour_is_a_new_row(env):
    put(env, NOW - 60)
    (env / CH.RATE).write_text("2026-11-04 07:01 89 s81=36 head=4+5t qc=12 kv=20 hbm=12\n")
    assert CH.run(NOW, None, lambda: 0) == 0
    assert len(rows(env)) == 2


def test_stop_file(env):
    put(env, NOW - 3600)
    (env / "state").mkdir()
    (env / "state" / "count_hourly.stop").write_text("")
    assert CH.run(NOW, lambda: pytest.fail("scanned"), lambda: pytest.fail("committed")) == 0


def test_older_free_text_rows_do_not_break_it(env):
    put(env, NOW - 60)
    (env / CH.RATE).write_text("time\tdie\tsigned_types\tsigned_cores\n2026-11-03 18:34 PST\tS81 0/205\n")
    assert CH.run(NOW, None, lambda: 0) == 0
    assert len(rows(env)) == 3
