"""BIND-REPORT-STALE-1123: a bind run puts the previous OUT/bind_report.json aside at start; a reader refuses a report older than the run."""
import json
import os
import time

import pytest

import bind
import bind_report_fresh as BRF


def test_set_aside_renames_and_keeps_shared_inode(tmp_path):
    rep = tmp_path / "bind_report.json"
    rep.write_text('{"n_errors": 0}')
    shared = tmp_path / "published_copy.json"
    os.link(rep, shared)                                   # bind_share hardlinks: the shared inode is never rewritten
    prev = BRF.set_aside(tmp_path)
    assert prev == tmp_path / "bind_report.json.prev" and not rep.exists()
    assert json.loads(prev.read_text()) == {"n_errors": 0} and shared.read_text() == '{"n_errors": 0}'
    assert BRF.set_aside(tmp_path) is None                 # nothing there: nothing to do


def test_check_fresh_refuses_old_and_missing(tmp_path):
    t0 = time.time()
    with pytest.raises(BRF.StaleBindReport, match="^BIND-REPORT-STALE .*no report from this bind run"):
        BRF.check_fresh(tmp_path, t0)
    rep = tmp_path / "bind_report.json"
    rep.write_text('{"n_errors": 0}')
    os.utime(rep, (t0 - 5 * 3600, t0 - 5 * 3600))           # the 11:11 report a 16:00 run must not read
    with pytest.raises(BRF.StaleBindReport, match="^BIND-REPORT-STALE .*before this bind run started"):
        BRF.load_fresh(tmp_path, t0)
    os.utime(rep, (t0 - 0.5, t0 - 0.5))                     # coarse timestamps inside the slack count as this run
    assert BRF.load_fresh(tmp_path, t0) == {"n_errors": 0}
    rep.write_text('{"n_errors": 3}')
    assert BRF.load_fresh(tmp_path, t0) == {"n_errors": 3}


@pytest.mark.parametrize("cmd", ["bind", "all"])
def test_crashed_bind_leaves_no_old_report(tmp_path, monkeypatch, cmd):
    out = tmp_path / "out"
    out.mkdir()
    (out / "bind_report.json").write_text('{"n_errors": 0, "errors": []}')
    plan = tmp_path / "plan.json"
    plan.write_text("{}")

    def crash(a):
        raise KeyError("EMIT crash")                       # not a BindError: the run dies before writing its report
    monkeypatch.setattr(bind, "_pg_run", lambda a: 0)
    monkeypatch.setattr(bind, "cmd_elab", lambda a: 0)
    monkeypatch.setattr(bind, "cmd_bind", crash)
    with pytest.raises(KeyError):
        bind.main([cmd, str(plan), "--out", str(out)])
    assert not (out / "bind_report.json").exists()
    assert json.loads((out / "bind_report.json.prev").read_text())["n_errors"] == 0
    with pytest.raises(BRF.StaleBindReport):
        BRF.load_fresh(out, time.time())


def test_other_commands_keep_the_report(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    (out / "bind_report.json").write_text('{"n_errors": 0}')
    plan = tmp_path / "plan.json"
    plan.write_text("{}")
    monkeypatch.setattr(bind, "cmd_portbind", lambda a: 0)
    assert bind.main(["portbind", str(plan), "--out", str(out)]) == 0
    assert (out / "bind_report.json").exists() and not (out / "bind_report.json.prev").exists()
