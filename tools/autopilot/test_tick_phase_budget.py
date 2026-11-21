"""FLOW-OPS-1000: tick phase budgets (PHASE-OVERRUN) and stack dumps"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as A  # noqa: E402


def test_hard_budget_cuts_a_hung_phase_and_names_the_line(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "AP_DIR", tmp_path)
    logs = []
    monkeypatch.setattr(A, "log", lambda m: logs.append(m))
    monkeypatch.setitem(A.PHASE_BUDGET_S, "loop_gaps", 1)
    monkeypatch.setattr(A, "PHASE_HARD_X", 1.0)

    def hang():
        t = time.time()
        while time.time() - t < 30:                    # busy loop, like the 08:47 tick
            pass
        return "never"
    t0 = time.time()
    assert A.run_phase("loop_gaps", hang) is None
    assert time.time() - t0 < 10
    assert any(m.startswith("PHASE-OVERRUN loop_gaps") and "hang" in m for m in logs), logs
    assert "PHASE-OVERRUN loop_gaps" in (tmp_path / "tick_stack.log").read_text()


def test_soft_budget_and_inner_except_exception_does_not_swallow(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "AP_DIR", tmp_path)
    monkeypatch.setattr(A, "log", lambda m: None)
    monkeypatch.setitem(A.PHASE_BUDGET_S, "under_use", 1)
    monkeypatch.setattr(A, "PHASE_HARD_X", 2.0)
    seen = []

    def phase():
        try:
            while True:
                if A.phase_late():
                    seen.append("late")
                    return "soft"
                time.sleep(0.05)
        except Exception:                               # noqa: an inner broad handler must not eat PhaseOverrun
            return "swallowed"
    assert A.run_phase("under_use", phase) == "soft"
    assert seen == ["late"]
    assert not A.phase_late()


def test_launching_phases_are_never_hard_cut(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "AP_DIR", tmp_path)
    monkeypatch.setattr(A, "log", lambda m: None)
    monkeypatch.setitem(A.PHASE_BUDGET_S, "admit_new", 1)
    monkeypatch.setattr(A, "PHASE_HARD_X", 1.0)
    t = time.time()

    def submit():
        while time.time() - t < 2.5:
            pass
        return 3
    assert A.run_phase("admit_new", submit) == 3


def test_off_switch(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "AP_DIR", tmp_path)
    monkeypatch.setenv("AP_PHASE_BUDGETS", "0")
    assert A.run_phase("under_use", lambda: 7) == 7
    assert not A.phase_late()
