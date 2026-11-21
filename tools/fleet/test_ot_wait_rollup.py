"""FLOW-OPS-1300: per-host ot-wait ledgers fold into lanes/WAITS.tsv (dedup, window, unreadable host keeps its rows)."""
import os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import ot_wait_rollup as W

L = W.HEADER + "\n2026-11-21 11:50:16\ttolerant-swine\t-\tpid\t195129\t124\t170\tyes\t-\n2026-11-21 11:53:43\ttolerant-swine\tFAM-S81-SERDES-R6\tpid\t1000025\t0\t225\tno\t-\n"


def test_parse_and_merge():
    rows = W.parse(L)
    assert len(rows) == 2 and not any(r.startswith("time\t") for r in rows)
    now = time.mktime(time.strptime("2026-11-22 00:00:00", "%Y-%m-%d %H:%M:%S"))
    old = ["2026-11-01 00:00:00\th\tX\tpid\t1\t0\t1\tno\t-", rows[0]]
    m = W.merge(old, {"epyc7": rows, "epyc8": None}, now=now, days=7)
    assert m == sorted(rows)                                                 # dedup, the 11-01 row is out of the 7-day window
    keep = W.merge([rows[1]], {"epyc8": None}, now=now)                       # unreadable host: its rows already in WAITS.tsv stay
    assert keep == [rows[1]]


def test_main_writes_once_and_commits(tmp_path, monkeypatch):
    (tmp_path / "lanes").mkdir(); (tmp_path / "bin").mkdir()
    (tmp_path / "bin/coord-commit.sh").write_text("echo PUSHED x >> " + str(tmp_path / "commits") + "; echo PUSHED x\n")
    monkeypatch.setattr(W, "read_host", lambda h: W.parse(L))
    assert W.main(["--coord", str(tmp_path), "--days", "100000", "epyc7"]) == 0
    t = (tmp_path / "lanes/WAITS.tsv").read_text().splitlines()
    assert t[0] == W.HEADER and len(t) == 3
    assert W.main(["--coord", str(tmp_path), "--days", "100000", "epyc7"]) == 0
    assert (tmp_path / "commits").read_text().count("PUSHED") == 1          # unchanged: no second commit
