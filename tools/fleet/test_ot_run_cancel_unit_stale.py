"""FLEET-WATCH-R5 11-21: ot-run --cancel <exact unit> also stops the scope by unit when only stale clients match, and exits 3 while a scope is still active."""
import importlib.machinery, importlib.util, pathlib, types
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_cancel_unit2", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_cancel_unit2", l)); l.exec_module(RUN)
UNIT = "oth-ubuntu-284665-1795150612"


def setup(monkeypatch, out):
    calls = []
    monkeypatch.setattr(RUN, "clients", lambda: {9: ([UNIT, "--dir", "/srv/x/r8b"], "/srv/x/r8b")})   # a stale client whose args name the unit
    monkeypatch.setattr(RUN.os, "kill", lambda p, s: None)
    monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    monkeypatch.setattr(RUN, "stop_started", lambda t, **k: None)
    monkeypatch.setattr(RUN, "stop_by_path", lambda paths, **k: [])
    monkeypatch.setattr(RUN, "_host_run", lambda run, h, cmd: (calls.append((h, cmd)), types.SimpleNamespace(stdout=out, stderr=""))[1])
    return calls


def test_stale_client_match_still_stops_the_scope_by_unit(monkeypatch):
    calls = setup(monkeypatch, "1 scope(s) stopped\ncontainers stopped: dpkit-x\n")
    assert RUN.cancel(UNIT, False) == 0
    assert calls and all(f"ot-heavy-stop --unit {UNIT}" in c for _h, c in calls)


def test_scope_still_running_after_cancel_is_nonzero(monkeypatch):
    setup(monkeypatch, "STILL RUNNING after kill\n")
    assert RUN.cancel(UNIT, False) == 3


def test_non_unit_selector_does_not_call_the_unit_path(monkeypatch):
    calls = setup(monkeypatch, "")
    monkeypatch.setattr(RUN, "clients", lambda: {9: (["k.sh", "--dir", "/srv/x/r8b"], "/srv/x/r8b")})
    assert RUN.cancel("k.sh", False) == 0 and not calls
