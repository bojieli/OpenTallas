"""P-FLEET-LOCALITY: the Explorer fleet probe never touches epyc9 or epyc2 by default."""
import importlib.util, os, pathlib, sys

SERVER = pathlib.Path(__file__).resolve().parent / "server.py"


def _hosts(env):
    src = SERVER.read_text()
    start = src.index("PROBE_EXCLUDE = ")
    end = src.index("_FLEET = {}")
    old = dict(os.environ)
    os.environ.pop("FLEET_PROBE_EXCLUDE", None); os.environ.pop("FLEET_PROBE_HOSTS", None)
    os.environ.update(env)
    try:
        ns = {"os": os}
        exec(src[start:end], ns)
        return ns["PROBE_HOSTS"]
    finally:
        os.environ.clear(); os.environ.update(old)


def test_default_excludes_epyc9_and_epyc2():
    h = _hosts({})
    assert "epyc9" not in h and "epyc2" not in h
    assert {"intel1", "intel2", "epyc7", "epyc8", "epyc10", "epyc11", "epyc12"} <= set(h)


def test_exclude_override():
    assert "epyc2" in _hosts({"FLEET_PROBE_EXCLUDE": "epyc9"})
    assert "epyc9" not in _hosts({"FLEET_PROBE_EXCLUDE": "epyc9"})
