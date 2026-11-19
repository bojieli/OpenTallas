"""NOLOCALHOST-1119: localhost / the hub never admits a kit."""
import importlib.machinery, importlib.util, pathlib
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_nolh", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_nolh", l)); l.exec_module(RUN)


def test_default_pool_and_explicit_lists_drop_localhost(monkeypatch):
    monkeypatch.delenv("OT_RUN_ALLOW_LOCALHOST", raising=False)
    assert "localhost" not in RUN.HOSTS
    assert RUN.drop_no_heavy(["epyc2", "localhost", "epyc7"]) == ["epyc2", "epyc7"]
    assert RUN.drop_no_heavy(["localhost"]) == []                      # main() refuses this with NOT RUN


def test_allow_env_keeps_localhost_for_a_light_probe(monkeypatch):
    monkeypatch.setenv("OT_RUN_ALLOW_LOCALHOST", "1")
    assert RUN.drop_no_heavy(["localhost", "epyc2"]) == ["localhost", "epyc2"]


def test_kit_wave_capacity_pool_has_no_hub():
    src = (H.parent / "autopilot" / "kit_wave.py").read_text()
    assert 'if h not in (hub, "localhost")]' in src
