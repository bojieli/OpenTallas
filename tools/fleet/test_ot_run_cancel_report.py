"""CANCEL-REPORT-1124: a cancel whose scope already ended (client SIGTERM first, or stopped moments before) reports CANCELLED, not 'nothing found'."""
import importlib.machinery, importlib.util, pathlib, types
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_cancel_report", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_cancel_report", l)); l.exec_module(RUN)
UNIT = "oth-ubuntu-3316149-1795553941"


def fake(show):
    def _hr(run, h, cmd, timeout=180):
        if cmd.startswith("systemctl --user show"):
            return types.SimpleNamespace(stdout=show.get(h, "LoadState=not-found\nActiveState=inactive\n"), stderr="")
        return types.SimpleNamespace(stdout="scopes stopped: none\ncontainers stopped: none\n", stderr="")
    return _hr


def test_unit_that_already_ended_is_reported_cancelled(monkeypatch, capsys):
    monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    monkeypatch.setattr(RUN, "_host_run", fake({"epyc9": "LoadState=loaded\nActiveState=failed\nResult=signal\n"}))
    assert RUN.cancel_unit(UNIT, fleet=["epyc8", "epyc9"]) == 0
    out = capsys.readouterr().out
    assert "CANCELLED" in out and "epyc9 (failed/signal)" in out and "nothing found" not in out


def test_follow_up_after_client_sigterm_is_cancelled(monkeypatch, capsys):
    monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    monkeypatch.setattr(RUN, "_host_run", fake({}))
    assert RUN.cancel_unit(UNIT, fleet=["epyc9"], after_client=[4242]) == 0
    assert "after SIGTERM to its client(s) [4242]" in capsys.readouterr().out


def test_unknown_unit_is_still_nothing_found(monkeypatch, capsys):
    monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    monkeypatch.setattr(RUN, "_host_run", fake({}))
    assert RUN.cancel_unit(UNIT, fleet=["epyc9"]) == 1
    assert "nothing found" in capsys.readouterr().out
