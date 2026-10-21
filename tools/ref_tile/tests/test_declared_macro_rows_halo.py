"""Declared SRAM pin-face halos must reach tapcell row cutting with fixed macro placement."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ref_tile as RT


def env(route, blocks=True):
    spec = dict(name="halo_probe", top="halo_probe", kind="tile", sources=[], params={}, pins={}, inter=[],
                clock_port="clk", clock="cts", route=route)
    return RT.gen_env(spec, "physical/ref_tile/halo_probe", 216, 216, dict(rlayers=["M2", "M5"]),
                      [dict(view="physical/probe_view")] if blocks else [])


def test_declared_asymmetric_halo_reaches_row_cut():
    text = env(dict(macro_halo_um=5.4, macro_halo_x_um=10.8))
    assert "MACRO_ROWS_HALO_X=10.8" in text
    assert "MACRO_ROWS_HALO_Y=5.4" in text


def test_declared_uniform_and_x_only_halos():
    assert "MACRO_ROWS_HALO_X=10.8" in env(dict(macro_halo_um=10.8))
    assert "MACRO_ROWS_HALO_Y=10.8" in env(dict(macro_halo_um=10.8))
    assert "MACRO_ROWS_HALO_Y=2" in env(dict(macro_halo_x_um=10.8))


def test_undeclared_or_no_macros_preserves_platform_defaults():
    assert "MACRO_ROWS_HALO" not in env({})
    assert "MACRO_ROWS_HALO" not in env(dict(macro_halo_um=10.8), blocks=False)
