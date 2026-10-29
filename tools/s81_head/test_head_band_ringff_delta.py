"""DIE-HEAD-21 HK3: head_band_ringff_delta.py unit tests (synthetic type, no EDA tools)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import head_band_ringff_delta as B  # noqa: E402


def _type(core=None):
    band = dict(rect_um=[17.28, 100.0, 30.24, 300.0], width=514, ring_width=576, live_data_storage_flops=2570,
                area_reserve_um2=2636.064, instance="u_cland_c_i", max_pin_to_band_hop_um=133.0)
    t = dict(outline_um=[800.0, 600.0], buses=[dict(name="c_i", face="W", window_um=[100.0, 300.0], width=514)],
             clock=dict(die_islands_um=[[60.0, 150.0, 70.0, 160.0]],
                        reserved_sites_um=[dict(rect_um=[17.28, 100.0, 30.24, 300.0], kind="landing_ring_bank",
                                                ref="u_cland_c_i")],
                        landing_contract=dict(bands={"c_i": band},
                                              collector_local_sources=[dict(name="c_i", band=dict(band))])),
             hard_cores=core or [])
    return t


def test_ringff_spread_band_sized_and_off_island():
    t = _type()
    new, fail = B.compose_bands(t, 2.0, "ff")
    assert not fail
    nb = new["c_i"]
    r = nb["rect_um"]
    reserve = (5 * 576 + 160) * B.CLP.RING_FF_RESERVE_UM2 * B.CLP.RING_FF_PACK
    assert abs(nb["area_reserve_um2"] - reserve) < 0.01
    assert (r[2] - r[0]) * (r[3] - r[1]) >= 1.9 * reserve and nb["ring_place"] == "ff" and nb["spread"] >= 1.9
    assert not B.D.ov(r, (60.0, 150.0, 70.0, 160.0), -1e-6)        # island kept out
    assert nb["instance"] == "u_cland_c_i" and nb["max_pin_to_band_hop_um"] <= 405
    assert B.CLP.BAND_RESERVE == "padded" and B.CLP.BAND_SPREAD == 1.0   # module globals restored


def test_apply_updates_contract_source_and_reserved_bank():
    t = _type()
    new, _ = B.compose_bands(t)
    assert B.apply_bands(t, new) == 1
    lc = t["clock"]["landing_contract"]
    r = new["c_i"]["rect_um"]
    assert lc["bands"]["c_i"]["rect_um"] == r and lc["collector_local_sources"][0]["band"]["rect_um"] == r
    assert t["clock"]["reserved_sites_um"][0]["rect_um"] == r


def test_fixed_core_is_obstacle_sram_is_not():
    core = [dict(inst="u_pair", module="ot_pair", origin_um=[43.2, 80.0], outline_um=[300.0, 300.0])]
    sram = [dict(inst="u_m", module="ot_sram_x", lef="x.lef", origin_um=[40.0, 120.0], outline_um=[50.0, 50.0])]
    new, fail = B.compose_bands(_type(core + sram))
    assert not fail
    r = new["c_i"]["rect_um"]
    assert not B.D.ov(r, (43.2, 80.0, 343.2, 380.0), -1e-6)        # band avoids the fixed core
    assert len(B.fixed_view(_type(core + sram))["hard_cores"]) == 1
