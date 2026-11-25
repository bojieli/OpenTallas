"""COORD 11-25 item 42: stall_watch probes the nine live hosts (hub as localhost) and never a terminated one."""
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def load(monkeypatch, hub="intel2", live=None):
    monkeypatch.setenv("OT_HUB_NAME", hub)
    if live is None:
        monkeypatch.delenv("OT_LIVE_HOSTS", raising=False)
    else:
        monkeypatch.setenv("OT_LIVE_HOSTS", live)
    sys.modules.pop("stall_watch", None)
    return importlib.import_module("stall_watch")


def test_default_hosts_are_the_nine_live_hosts(monkeypatch):
    sw = load(monkeypatch)
    names = [("intel2" if h == "localhost" else h) for h in sw.DEFAULT_HOSTS]
    assert sorted(names) == sorted(["intel1", "intel2", "epyc2", "epyc7", "epyc8", "epyc9", "epyc10", "epyc11", "epyc12"])
    assert len(sw.DEFAULT_HOSTS) == 9 and sw.DEFAULT_HOSTS[0] == "localhost" and "intel2" not in sw.DEFAULT_HOSTS


def test_never_a_terminated_host(monkeypatch):
    sw = load(monkeypatch)
    assert not {"epyc3", "epyc4", "epyc5", "epyc6"} & set(sw.DEFAULT_HOSTS)


def test_env_override(monkeypatch):
    sw = load(monkeypatch, live="intel1 epyc7")
    assert sw.DEFAULT_HOSTS == ["localhost", "intel1", "epyc7"]
