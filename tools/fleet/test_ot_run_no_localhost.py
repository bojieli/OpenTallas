"""NOLOCALHOST-1119: heavy jobs are banned on rtx-pro (by machine identity); the hub's localhost (intel2, capped build host) keeps admitting."""
import importlib.machinery, importlib.util, pathlib
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_nolh", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_nolh", l)); l.exec_module(RUN)


def test_on_rtx_pro_localhost_leaves_every_pool(monkeypatch):
    monkeypatch.delenv("OT_RUN_ALLOW_LOCALHOST", raising=False)
    assert RUN.drop_no_heavy(["epyc2", "localhost", "epyc7"], node="ubuntu") == ["epyc2", "epyc7"]
    assert RUN.drop_no_heavy(["localhost"], node="ubuntu") == []                       # main() refuses this with NOT-RUN / 78


def test_on_the_hub_localhost_stays_a_capped_build_host(monkeypatch):
    monkeypatch.delenv("OT_RUN_ALLOW_LOCALHOST", raising=False)
    assert RUN.drop_no_heavy(["epyc2", "localhost"], node="tolerant-swine") == ["epyc2", "localhost"]
    assert "localhost" in RUN.HOSTS


def test_allow_env_keeps_localhost_for_a_light_probe_on_rtx_pro(monkeypatch):
    monkeypatch.setenv("OT_RUN_ALLOW_LOCALHOST", "1")
    assert RUN.drop_no_heavy(["localhost", "epyc2"], node="ubuntu") == ["localhost", "epyc2"]


def test_kit_wave_keeps_the_hub_in_its_capacity_pool():
    src = (H.parent / "autopilot" / "kit_wave.py").read_text()
    assert 'hosts = [("localhost" if h == hub else h) for h in opt(cfg, die, "hosts")]' in src
