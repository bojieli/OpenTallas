"""COORD 2026-10-26: HBM hard-core kits route to M5; a plan pin above the ceiling fails generation (no clamp)."""
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GENS = [load("coregen_ceiling", HERE / "gen_core_kit_hbm.py"),
        load("harden_ceiling", HERE.parent / "hbm" / "cores" / "harden" / "gen_core_kit.py")]
TKM = load("tkm_build_ceiling", HERE.parent / "hbm" / "tkm_noid_kits" / "build_kit.py")
PINS = [dict(name="a", layer="M3", x=1, y=0), dict(name="b", layer="M4", x=0, y=1), dict(name="c", layer="M5", x=1, y=0)]


@pytest.mark.parametrize("gen", GENS)
def test_default_ceiling_m5_and_pins_at_or_below_pass(gen):
    assert gen.HBM_CORE_ROUTE_CEILING == "M5"
    gen.check_route_ceiling(PINS, "M5", "t")
    gen.check_cfg_ceiling(["export MIN_ROUTING_LAYER = M2", "export MAX_ROUTING_LAYER = M5"], "M5", "t")


@pytest.mark.parametrize("gen", GENS)
@pytest.mark.parametrize("layer", ["M6", "M7"])
def test_pin_above_ceiling_fails(gen, layer):
    with pytest.raises(SystemExit, match="PIN_ABOVE_CEILING"):
        gen.check_route_ceiling(PINS + [dict(name="clk", layer=layer, x=0, y=0)], "M5", "t")


@pytest.mark.parametrize("gen", GENS)
def test_config_override_or_bad_ceiling_fails(gen):
    with pytest.raises(SystemExit, match="ROUTE_CEILING"):
        gen.check_cfg_ceiling(["export MAX_ROUTING_LAYER = M5", "export MAX_ROUTING_LAYER = M7"], "M5", "t")
    with pytest.raises(SystemExit, match="ROUTE_CEILING"):
        gen.check_cfg_ceiling(["export MIN_ROUTING_LAYER = M2"], "M5", "t")
    with pytest.raises(SystemExit, match="ROUTE_CEILING"):
        gen.check_route_ceiling(PINS, "M4", "t")      # below the M5 core PG pin layer


@pytest.mark.parametrize("gen", GENS)
@pytest.mark.parametrize("ceiling", ["M6", "M7"])
def test_explicit_upper_layer_override_fails(gen, ceiling):
    # The die GRT0 proof depends on every core leaving M6+ available. An explicit
    # override must not restore the obstruction that the approved plan removed.
    with pytest.raises(SystemExit, match="ROUTE_CEILING"):
        gen.check_route_ceiling(PINS, ceiling, "t")


def _tkm_kit(tmp_path, clk_layer="M4", cfg="export MAX_ROUTING_LAYER = M5\n"):
    (tmp_path / "pins.json").write_text(json.dumps([dict(bus="tile_clk", bit=None, layer=clk_layer, x=319.68,
                                                         y=172.728, face="E")]))
    (tmp_path / "io.tcl").write_text(f"place_pin -pin_name {{tile_clk}} -layer {clk_layer} -location {{319.5840 "
                                     "172.7280} -pin_size {0.1920 0.0240}\n")
    (tmp_path / "config.mk").write_text("export MIN_ROUTING_LAYER = M2\n" + cfg)
    return tmp_path


def test_tkm_kit_ceiling(tmp_path):
    TKM.check_route_ceiling(_tkm_kit(tmp_path))
    with pytest.raises(SystemExit, match="PIN_ABOVE_CEILING"):
        TKM.check_route_ceiling(_tkm_kit(tmp_path, clk_layer="M6"))
    with pytest.raises(SystemExit, match="ROUTE_CEILING"):
        TKM.check_route_ceiling(_tkm_kit(tmp_path, cfg="export MAX_ROUTING_LAYER = M7\n"))
    with pytest.raises(SystemExit, match="ROUTE_CEILING"):
        TKM.check_route_ceiling(_tkm_kit(tmp_path, cfg="export MAX_ROUTING_LAYER = M5\noverride export MAX_ROUTING_LAYER = M7\n"))


def test_committed_tkm_sources_meet_ceiling():
    root = HERE.parent / "hbm" / "tkm_noid_kits"
    for kind in ("common", "terminal"):
        TKM.check_route_ceiling(root / kind)
    assert "MAX_ROUTING_LAYER" not in (root / "clock" / "config_append.mk").read_text()
