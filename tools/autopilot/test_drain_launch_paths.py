"""FLOW-OPS-0900 fix 4: every launch path takes its hosts through the one drain filter (host_drain.py): wave gen hosts, queued-wait repick,
auto-resign (DB host draining -> staged any-host form), ot-run --hosts refusal."""
import importlib.machinery, importlib.util, json, os, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "fleet"))
import kit_wave as KW
import auto_resign as AR
import host_drain as HD

STT = {"intel1": {"admit": 27, "load": 78.0, "cores": 112, "run": 31, "scratch_gb": 100},
       "epyc10": {"admit": 24, "load": 90.0, "cores": 96, "run": 41, "scratch_gb": 391},
       "localhost": {"admit": 349, "load": 66.0, "cores": 112, "run": 15, "scratch_gb": 1275}}


def test_draining_hosts_merges_die_and_fleet_caps(monkeypatch):
    monkeypatch.setattr(HD, "load_caps", lambda: {"epyc10": 500})
    assert KW.draining_hosts({"intel1": 250}, STT, "intel2") == {"intel1", "epyc10"}
    monkeypatch.setattr(HD, "load_caps", lambda: {})
    assert KW.draining_hosts({"intel1": 250}, STT, "intel2") == {"intel1"}
    assert KW.draining_hosts({"intel1": 50}, STT, "intel2") == set()


def test_auto_resign_db_host_draining_goes_any_host(monkeypatch):
    monkeypatch.setattr(HD, "load_caps", lambda: {"intel1": 250})
    assert AR.host_draining(STT, "intel1") is True and AR.host_draining(STT, "epyc10") is False and AR.host_draining({}, "intel1") is False


def _otrun():
    l = importlib.machinery.SourceFileLoader("ot_run_drain", str(HERE.parent / "fleet" / "ot-run"))
    m = importlib.util.module_from_spec(importlib.util.spec_from_loader(l.name, l))
    l.exec_module(m)
    return m


def test_ot_run_refuses_a_pin_to_a_draining_host_and_keeps_existing_dirs(monkeypatch, capsys):
    M = _otrun()
    monkeypatch.setattr(M, "drain_state", lambda hosts: (HD, {"intel1": (100, 250)}))
    monkeypatch.setattr(M, "dir_has_data", lambda h, d: d == "/srv/opentallas-scratch2/claude/L/old")
    hosts = ["intel1", "epyc10"]
    assert M.drain_hosts(hosts, "/srv/opentallas-scratch2/claude/L/new", None) == ["epyc10"]
    assert M.drain_hosts(hosts, "/srv/opentallas-scratch2/claude/L/old", None) is hosts            # its --dir already holds data there
    exits = []
    monkeypatch.setattr(M, "not_run", lambda reason, code=0: (exits.append(reason), (_ for _ in ()).throw(SystemExit(77)))[1])
    try:
        M.drain_hosts(["intel1"], "/srv/opentallas-scratch2/claude/L/new", None)
    except SystemExit:
        pass
    assert exits and "intel1 DRAINING (100 of 250 GB scratch free)" in exits[0] and "--hosts" in exits[0]
    exits.clear()
    try:
        M.drain_hosts(["intel1"], M.JOB_ROOT, "/spec.json")                                         # a sealed job never 'holds data' there
    except SystemExit:
        pass
    assert exits
