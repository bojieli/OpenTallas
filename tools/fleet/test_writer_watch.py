import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import writer_watch as W

GB = 1e9


def S(t, gb, dt=600):
    return {"t": t, "dt": dt, "bytes": gb * GB}


def test_rate_full_window():
    now = 10000
    s = [S(now - 600 * i, 10) for i in range(6)]  # 60 GB in an hour
    assert abs(W.rate_gb_h(s, now) - 60) < 1


def test_rate_short_history():
    assert abs(W.rate_gb_h([S(1000, 10)], 1000) - 60) < 1  # 10 GB in 10 min


def test_rate_old_samples_dropped():
    assert W.rate_gb_h([S(0, 500)], 7200) == 0.0


def test_should_post():
    assert W.should_post(51, None, 0)
    assert not W.should_post(50, None, 0)
    assert not W.should_post(80, 0, 3600)
    assert W.should_post(80, 0, 3 * 3600)


def test_decide_once_per_3h():
    st = {"lanes": {"A": {"samples": [S(1000, 20)], "top": "d"}, "B": {"samples": [S(1000, 1)]}}}
    assert [x[0] for x in W.decide(st, "h", 1000)] == ["A"]
    assert W.decide(st, "h", 1100) == []


def test_run_once_fake_clock(tmp_path):
    base = tmp_path / "claude"
    (base / "L1" / "big").mkdir(parents=True)
    (base / "L1" / "rt").mkdir()
    (base / "L1" / "rt" / "x").write_bytes(b"x" * 1000)
    f = base / "L1" / "big" / "f"
    f.write_bytes(b"x" * 4096)
    now = 1e9
    os.utime(f, (now, now))
    os.utime(base / "L1" / "big", (now, now))
    old = base / "L1" / "big" / "old"
    old.write_bytes(b"y" * 4096)
    os.utime(old, (now - 5000, now - 5000))
    posts = []
    sp = str(tmp_path / "st.json")
    clk = lambda: now
    r = W.run_once(now, str(base), sp, "hostx", posts.append, lambda: 123.0, clk)
    assert r == []  # 4 KB is far below threshold
    st = W.load(sp)
    assert st["lanes"]["L1"]["samples"][-1]["bytes"] == 4096
    assert st["lanes"]["L1"]["top"] == "big"
    # force a post via synthetic huge sample
    st["lanes"]["L1"]["samples"].append(S(now + 600, 100))
    import json
    json.dump(st, open(sp, "w"))
    r = W.run_once(now + 600, str(base), sp, "hostx", posts.append, lambda: 123.0, lambda: now + 600)
    assert len(posts) == 1 and posts[0].startswith("WARN hostx lane L1 writes ") and "top dir big" in posts[0] and "free 123 GB" in posts[0]
    W.run_once(now + 1200, str(base), sp, "hostx", posts.append, lambda: 1.0, lambda: now + 1200)
    assert len(posts) == 1


def test_post_via_ssh():
    seen = []
    class R:
        returncode = 0
    W.post("m", "epyc7", lambda c, **k: seen.append(c) or R())
    assert seen[0][:4] == ["ssh", "-o", "BatchMode=yes", "intel2"]
