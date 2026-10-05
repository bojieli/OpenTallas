import json

import pytest

from tools import w13_chain_successor as chain


def test_ss_file_alone_never_reaches_worktree_creation_or_launch(tmp_path, monkeypatch):
    block = "ot_gpu_tc16"
    lib = tmp_path / chain.CHIP / "abstracts" / block / f"{block}_ss.lib"
    lib.parent.mkdir(parents=True)
    lib.write_text("an SS view exists despite incomplete evidence")
    monkeypatch.setattr(chain, "parked", lambda config: None)
    events = []
    monkeypatch.setattr(chain, "event", lambda config, name, **details: events.append(name))
    monkeypatch.setattr(chain.subprocess, "run", lambda *args, **kwargs: pytest.fail("reached mutation before qualification"))
    branch = {"name": "v", "handles": [], "columns": [{"root": str(tmp_path), "block": block, "sources": ["rtl/top.sv"]}]}
    assert chain.run_branch({}, branch) is False
    assert events == ["waiting", "column_gate", "blocked"]


def test_failed_gate_never_reaches_launch(tmp_path, monkeypatch):
    monkeypatch.setattr(chain, "parked", lambda config: None)
    monkeypatch.setattr(chain, "event", lambda *args, **kwargs: None)
    monkeypatch.setattr(chain, "audits", lambda branch: [{"passed": False, "issues": ["failed_signoff_verdict"]}])
    monkeypatch.setattr(chain.subprocess, "run", lambda *args, **kwargs: pytest.fail("failed column reached mutation"))
    assert chain.run_branch({}, {"name": "q", "handles": []}) is False


def test_pid_reuse_is_not_a_live_column_handle(monkeypatch):
    monkeypatch.setattr(chain, "identity", lambda pid: {"pid": pid, "start_ticks": "new", "state": "S"})
    assert not chain.running({"pid": 5, "start_ticks": "old"})
    assert chain.running({"pid": 5, "start_ticks": "new"})


def test_predecessor_cannot_resume_or_change_identity(monkeypatch):
    config = {"predecessor": [{"pid": 5, "start_ticks": "old"}]}
    monkeypatch.setattr(chain, "identity", lambda pid: {"pid": pid, "start_ticks": "old", "state": "T"})
    chain.parked(config)
    monkeypatch.setattr(chain, "identity", lambda pid: {"pid": pid, "start_ticks": "old", "state": "S"})
    with pytest.raises(RuntimeError, match="no longer parked"):
        chain.parked(config)


def test_boundary_failure_rejects_even_a_passing_corner(tmp_path, monkeypatch):
    monkeypatch.setattr(chain, "check", lambda *args: {"passed": True, "issues": []})
    path = tmp_path / chain.CHIP / "blocks" / "ot_gpu_tc16.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"block": "ot_gpu_tc16", "clock_period_ns": 0.833, "closed_against_budget": False}))
    row = chain.qualify(tmp_path, "ot_gpu_tc16", [])
    assert not row["passed"]
    assert "block_boundary_or_clock_not_closed" in row["issues"]
