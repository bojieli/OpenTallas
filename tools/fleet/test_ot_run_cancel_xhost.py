"""CANCEL-XHOST-1124: --cancel finds a client on ANOTHER node from the selector (tag names its node; an admitted unit is looked up in every
fleet host's running ot-status records, whatever rt started the client) and runs the same cancel there once; a RESULT line says what
happened to the signalled client instead of leaving '0 scope(s) stopped' as the last word."""
import importlib.machinery, importlib.util, os, pathlib, types

H = pathlib.Path(__file__).parent
ld = importlib.machinery.SourceFileLoader("ot_run_xhost", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_xhost", ld)); ld.exec_module(RUN)


def _me(monkeypatch, node="dear-crayfish"):
    monkeypatch.setattr(RUN, "_this_node", lambda: {node})


def test_tag_names_the_other_node_without_any_lookup(monkeypatch):
    _me(monkeypatch)
    monkeypatch.setattr(RUN.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no lookup for a tag")))
    assert RUN.remote_clients("otrun-tolerant-swine-94665-576555676") == [("intel2", "tolerant-swine", 94665)]
    assert RUN.remote_clients("otrun-key-cardinal-3395865-") == [("intel1", "key-cardinal", 3395865)]
    assert RUN.remote_clients("otrun-dear-crayfish-77-") == []                 # this node: the local match handles it
    assert RUN.remote_clients("dpkit") == [] and RUN.remote_clients("/srv/x") == []


def test_unit_is_found_in_the_running_status_records_of_any_host(monkeypatch):
    _me(monkeypatch)
    seen = []

    def run(cmd, **k):
        seen.append((cmd[-2], cmd[-1]))
        out = "otrun-tolerant-swine-94665.json\n" if cmd[-2] == "intel2" else ""
        return types.SimpleNamespace(stdout=out, stderr="", returncode=0)
    monkeypatch.setattr(RUN.subprocess, "run", run)
    assert RUN.remote_clients("oth-ubuntu-337541-1795576556") == [("intel2", "tolerant-swine", 94665)]
    q = dict(seen)["intel2"]
    assert '"unit": "oth-ubuntu-337541-1795576556"' in q and '"state": "running"' in q and "ot-status" in q
    assert "rt/" not in q                                                        # never keyed on the rt the client came from


def test_cancel_runs_on_the_clients_node_once_and_returns_its_rc(monkeypatch, capsys):
    _me(monkeypatch)
    monkeypatch.delenv("OT_RUN_CANCEL_NO_REMOTE", raising=False)
    monkeypatch.setattr(RUN, "clients", lambda: {}); monkeypatch.setattr(RUN, "log_signal", lambda m: None)
    monkeypatch.setattr(RUN, "unit_clients", lambda u: [])
    monkeypatch.setattr(RUN, "remote_clients", lambda s: [("intel2", "tolerant-swine", 94665)])
    monkeypatch.setattr(RUN, "cancel_unit", lambda *a, **k: (_ for _ in ()).throw(AssertionError("scope-only stop while the client lives elsewhere")))
    calls = []

    def run(cmd, **k):
        calls.append((cmd[-2], cmd[-1]))
        return types.SimpleNamespace(stdout="ot-run --cancel: RESULT: CANCELLED, client(s) [94665] exited\n", stderr="", returncode=0)
    monkeypatch.setattr(RUN.subprocess, "run", run)
    assert RUN.cancel("oth-ubuntu-337541-1795576556", False, reason="hang") == 0
    assert len(calls) == 1 and calls[0][0] == "intel2"
    c = calls[0][1]
    assert c.startswith("OT_RUN_CANCEL_NO_REMOTE=1 ") and "--cancel oth-ubuntu-337541-1795576556 --reason hang" in c
    o = capsys.readouterr().out
    assert "pid 94665 on tolerant-swine (intel2)" in o and "[intel2] ot-run --cancel: RESULT: CANCELLED" in o


def test_no_remote_hop_from_the_remote_side(monkeypatch):
    _me(monkeypatch)
    monkeypatch.setenv("OT_RUN_CANCEL_NO_REMOTE", "1")
    monkeypatch.setattr(RUN, "clients", lambda: {}); monkeypatch.setattr(RUN, "unit_clients", lambda u: [])
    monkeypatch.setattr(RUN, "remote_clients", lambda s: (_ for _ in ()).throw(AssertionError("second hop")))
    got = []
    monkeypatch.setattr(RUN, "cancel_unit", lambda sub, **k: got.append(sub) or 1)
    assert RUN.cancel("otrun-tolerant-swine-94665-", False) == 1 and got == ["otrun-tolerant-swine-94665-"]


def test_result_line_names_what_happened_to_the_client(capsys):
    assert RUN.client_exit_report([11, 12], wait_s=0, alive=lambda p: False) == []
    o = capsys.readouterr().out
    assert "RESULT: CANCELLED, client(s) [11, 12] exited" in o and "nothing was left to stop" in o
    assert RUN.client_exit_report([11, 12], wait_s=0, alive=lambda p: p == 12) == [12]
    assert "[12] still exiting" in capsys.readouterr().out


def test_kit_dir_selector_finds_a_client_on_another_node_and_ignores_wrappers():
    """FLEET-OPS 11-25: `ot-run --cancel /srv/.../it2` from the hub missed the queued clients on epyc8"""
    import types
    d = "/srv/opentallas-scratch2/claude/FP-CONVERGE-KV/it2"
    ps = (f"151343 python3 -I /x/rt/current/tools/fleet/ot-run --mem 24 --hosts epyc8 --dir {d} --max-wait 900 -- python3 plan_advisory.py\n"
          f"151344 bash -c cd {d} && python3 -I /x/ot-run --dir {d} -- true\n"
          f"151345 ssh epyc8 export X; ot-heavy --mem 24 --dir {d}\n"
          f"151346 python3 -I /x/rt/current/tools/fleet/ot-run --cancel {d}\n")
    def run(argv, **k):
        host = argv[-2] if argv[0] == "ssh" else "local"
        return types.SimpleNamespace(stdout=ps if host == "epyc8" else "", stderr="", returncode=0)
    got = RUN.remote_dir_clients(d, run=run, fleet=["epyc8", "epyc7"])
    assert got == [("epyc8", "epyc8", 151343)]
    assert RUN.remote_dir_clients("dpkit", run=run, fleet=["epyc8"]) == []
