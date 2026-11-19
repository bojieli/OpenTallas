"""CANCEL-STOP-1119: ot-run --cancel also stops the started job (ot-heavy-stop --match <its --dir>) on the client's hosts."""
import importlib.machinery, importlib.util, pathlib, types
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_cancel_stop", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_cancel_stop", l)); l.exec_module(RUN)


def test_targets_are_the_clients_own_tag_never_the_lane_dir():
    hit = {111: (["--mem", "48", "--hosts", "epyc2,epyc7", "--dir", "/srv/x/lane", "--", "bash", "bind.sh"], "/srv/x/lane"),
           222: (["--mem", "48", "--hosts", "epyc2", "--dir", "/srv/x/lane", "--", "bash", "proof.sh"], "/srv/x/lane")}
    got = RUN.stop_targets({111: hit[111]}, "bind", ["epyc8"], node="hub")
    assert got == [("epyc2", "otrun-hub-111-", 111), ("epyc7", "otrun-hub-111-", 111)]      # nothing names /srv/x/lane or pid 222: the proof kit is not matched
    assert all("lane" not in t for _, t, _p in got)


def test_stop_started_runs_ot_heavy_stop_over_ssh():
    calls = []
    RUN.stop_started([("epyc2", "/x/kit one", 1)], run=lambda cmd, **k: (calls.append(cmd), types.SimpleNamespace(stdout="ot-heavy-stop: 1 scope(s) stopped\n", stderr=""))[1])
    assert calls[0][-2] == "epyc2" and calls[0][-1] == "ot-heavy-stop --match '/x/kit one'"


def test_a_prefix_matching_two_clients_is_refused_without_all(monkeypatch, capsys):
    cl = {1: (["--hosts", "epyc2", "--dir", "/srv/x/lane", "--", "bash", "bind_a.sh"], "/srv/x/lane"), 2: (["--hosts", "epyc2", "--dir", "/srv/x/lane", "--", "bash", "bind_b.sh"], "/srv/x/lane")}
    monkeypatch.setattr(RUN, "clients", lambda: cl)
    killed = []
    monkeypatch.setattr(RUN.os, "kill", lambda p, s: killed.append(p))
    assert RUN.cancel("bind_", False) == 2 and killed == []
    assert "REFUSED" in capsys.readouterr().out
    monkeypatch.setattr(RUN, "stop_started", lambda t: None)
    monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    assert RUN.cancel("bind_a", False) == 0 and killed == [1]                                  # one exact job: fine
