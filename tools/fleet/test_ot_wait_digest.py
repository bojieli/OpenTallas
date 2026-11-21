"""FLOW-OPS-1000: ot-wait --digest (one wake for many targets) and the waits ledger"""
import importlib.machinery
import importlib.util
import json
import os
import sys
import types
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
ld = importlib.machinery.SourceFileLoader("ot_wait_cli", str(H / "ot-wait"))
sp = importlib.util.spec_from_loader("ot_wait_cli", ld)
W = importlib.util.module_from_spec(sp)
ld.exec_module(W)


def rec(d, name, **kw):
    r = dict(name=name, unit="oth-" + name, host="h", pid=999999999, pid_start=1, state="running")
    r.update(kw)
    (d / (name + ".json")).write_text(json.dumps(r))


def test_digest_returns_once_at_the_boundary_with_all_changes(tmp_path, capsys, monkeypatch):
    rec(tmp_path, "a", state="done", rc=0, t_end=1)
    rec(tmp_path, "b", state="done", rc=0, t_end=1)
    rec(tmp_path, "c")
    monkeypatch.setattr(W, "alive", lambda r: True)
    clock = [0.0]
    a = types.SimpleNamespace(dir=str(tmp_path), poll=60, every=30, timeout=0)
    rc, n = W.wait_digest(["a", "b", "c"], a, now=lambda: clock[0], sleep=lambda s: clock.__setitem__(0, clock[0] + s))
    out = capsys.readouterr().out
    assert (rc, n) == (75, 2) and clock[0] >= 1800
    assert out.count("DONE rc=0") == 2 and "RUNNING oth-c" in out and out.strip().endswith("REMAINING c")


def test_digest_all_ended_returns_at_once_with_first_failure(tmp_path, capsys, monkeypatch):
    rec(tmp_path, "a", state="done", rc=0, t_end=1)
    rec(tmp_path, "b", state="done", rc=2, t_end=1)
    a = types.SimpleNamespace(dir=str(tmp_path), poll=60, every=30, timeout=0)
    rc, n = W.wait_digest(["a", "b"], a, now=lambda: 0.0, sleep=lambda s: None)
    assert (rc, n) == (2, 2) and "REMAINING -" in capsys.readouterr().out


def test_ledger_line(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_WAIT_LEDGER", str(tmp_path / "w.tsv"))
    monkeypatch.setenv("OT_LANE", "FLOW-OPS-1000")
    W.ledger("digest", ["a", "b"], 124, 0.0, 0, 2)
    rows = (tmp_path / "w.tsv").read_text().splitlines()
    assert rows[0].startswith("time\thost\tlane") and "\tFLOW-OPS-1000\tdigest\ta,b\t124\t" in rows[1] and rows[1].split("\t")[7] == "yes"
