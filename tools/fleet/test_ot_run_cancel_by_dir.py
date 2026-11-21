"""FLEET-WATCH-R4 11-21: ot-run --cancel reaches the sealed container by the exact kit dir when its client is gone or only stale clients match."""
import importlib.machinery, importlib.util, pathlib, types
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_cancel_dir2", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_cancel_dir2", l)); l.exec_module(RUN)


def fake_run(calls, out="containers stopped: dpkit-x-1\n"):
    return lambda cmd, **k: (calls.append(cmd), types.SimpleNamespace(stdout=out, stderr=""))[1]


def test_stop_by_path_mounts_exact_dir_on_every_host():
    calls = []
    got = RUN.stop_by_path(["/srv/x/lane/r8b", "relative", None], run=fake_run(calls), fleet=["epyc2", "epyc9"])
    assert len(got) == 2 and all("-v /srv/x/lane/r8b:" in c[-1] for c in calls) and len(calls) == 2


def test_cancel_with_no_client_and_a_kit_dir_stops_its_container(monkeypatch):
    calls = []
    monkeypatch.setattr(RUN, "clients", lambda: {})
    monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    monkeypatch.setattr(RUN.subprocess, "run", fake_run(calls))
    assert RUN.cancel("/srv/x/lane/r8b", False) == 0 and calls


def test_cancel_with_a_stale_client_also_stops_by_its_dir(monkeypatch):
    seen = []
    monkeypatch.setattr(RUN, "clients", lambda: {9: (["--hosts", "epyc2", "--dir", "/srv/x/lane/r8b", "--", "bash", "k.sh"], "/srv/x/lane/r8b")})
    monkeypatch.setattr(RUN.os, "kill", lambda p, s: None)
    monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    monkeypatch.setattr(RUN, "stop_started", lambda t, **k: None)
    monkeypatch.setattr(RUN, "stop_by_path", lambda paths, **k: seen.extend(paths) or [])
    assert RUN.cancel("k.sh", False) == 0 and seen == ["/srv/x/lane/r8b"]


def test_no_container_found_returns_to_old_message(monkeypatch, capsys):
    monkeypatch.setattr(RUN, "clients", lambda: {})
    monkeypatch.setattr(RUN.subprocess, "run", fake_run([], "containers stopped: none\n"))
    assert RUN.cancel("/srv/x/none", False) == 1
