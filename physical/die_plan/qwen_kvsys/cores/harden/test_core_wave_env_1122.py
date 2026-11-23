"""WAVE-ENV-CORE-1122 (COORD, FABLE-KV-DIE): KV core kits write the env-only gen knobs into config.mk (the docker container gets no
host env, so OT_GRT_ALLOW_CONGESTION / OT_GRT_CONG_ITERS / OT_PGCAP* / OT_PLACE_MAX_FANOUT used to drop silently)."""
import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("gen_core_kit_kv_wenv", HERE / "gen_core_kit_kv.py")
G = importlib.util.module_from_spec(spec)
sys.modules["gen_core_kit_kv_wenv"] = G
spec.loader.exec_module(G)
KNOBS = ("OT_GRT_ALLOW_CONGESTION", "OT_GRT_CONG_ITERS", "OT_PGCAP", "OT_PGCAP_ADJ", "OT_PLACE_MAX_FANOUT")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for k in KNOBS:
        monkeypatch.delenv(k, raising=False)


def test_no_env_no_line():
    cfg = ["export PLATFORM = asap7"]
    assert G.wave_env_cfg(list(cfg)) == (cfg, {})
    assert G.core_place_max_fanout() == 64


def test_allow_congestion_iters_pgcap(monkeypatch):
    monkeypatch.setenv("OT_GRT_ALLOW_CONGESTION", "1")
    monkeypatch.setenv("OT_GRT_CONG_ITERS", "50")
    monkeypatch.setenv("OT_PGCAP", "1")
    monkeypatch.setenv("OT_PGCAP_ADJ", "0.5")
    cfg, ap = G.wave_env_cfg(["export PLATFORM = asap7"])
    assert "export GLOBAL_ROUTE_ARGS = -congestion_report_iter_step 5 -verbose -allow_congestion -congestion_iterations 50" in cfg
    assert "export OT_PGCAP = 1" in cfg and "export OT_PGCAP_ADJ = 0.5" in cfg
    assert ap == {"OT_GRT_ALLOW_CONGESTION": "1", "OT_GRT_CONG_ITERS": "50", "OT_PGCAP": "1", "OT_PGCAP_ADJ": "0.5"}
    assert cfg[-1].startswith("# WAVE-ENV-CORE-1122")


def test_recipe_route_args_kept_flag_added(monkeypatch):
    monkeypatch.setenv("OT_GRT_ALLOW_CONGESTION", "1")
    monkeypatch.setenv("OT_GRT_CONG_ITERS", "30")      # OpenROAD default: no flag
    cfg, ap = G.wave_env_cfg(["export GLOBAL_ROUTE_ARGS = -congestion_iterations 20 -verbose"])
    assert cfg[0] == "export GLOBAL_ROUTE_ARGS = -congestion_iterations 20 -verbose -allow_congestion"
    assert ap == {"OT_GRT_ALLOW_CONGESTION": "1"}


def test_fanout_and_pgcap_install(monkeypatch, tmp_path):
    monkeypatch.setenv("OT_PLACE_MAX_FANOUT", "32")
    assert G.core_place_max_fanout() == 32
    monkeypatch.setenv("OT_PLACE_MAX_FANOUT", "x")
    with pytest.raises(ValueError):
        G.core_place_max_fanout()
    (tmp_path / "config.mk").write_text("export OT_PGCAP = 1\n")
    (tmp_path / "grt_pre.tcl").write_text("# main\n")
    assert G._gen_phys().pgcap_install(tmp_path)
    assert (tmp_path / "pg_pair_cap.tcl").exists() and "ot_pgcap_add" in (tmp_path / "grt_pre.tcl").read_text()
