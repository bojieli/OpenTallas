"""DIE-KV-42 10-29 (KV-022 SD try3 3_5 DPL-0033): the PHY supply region that pdn.tcl writes as a HARD placement
blockage (gen_phys.phy_pg_pdn, die.pg.domains) can be wider than the PHY macro. (a) the landing band search treats it
as blocked; bands clear of it, and plans without one, stay byte-identical. (b) landing_placement.tcl fails closed when
a ring band overlaps a hard blockage it does not pack around."""
import copy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clock_landing_plan as CP  # noqa: E402
import schema as S  # noqa: E402

# type 400 x 300: a PHY macro (lef content) at (0, 40) 300 x 250; its supply region runs to x 390 (as KV sys_SD:
# macro to 1866.24, VDDPHY region to 1883.52). The landing bus sits on the E face at y 100..140.
GEOM = {"rx_i": dict(name="rx_i", face="E", window_um=[100.0, 140.0], width=1)}
PHY = [0.0, 40.0, 390.0, 300.0]


def _type():
    return dict(outline_um=[400.0, 300.0], hard_cores=[], buses=[],
                contents=[dict(inst="u_phy", lef="phy.lef", origin_um=[0.0, 40.0], outline_um=[300.0, 250.0])],
                clock=dict(landing_contract=dict(pins=[], bands={})), _cland_geom=copy.deepcopy(GEOM))


def _plan(domains):
    t = _type()
    t.pop("_cland_geom")
    return dict(die=dict(name="d", outline_um=[800.0, 300.0], reach_um=405.0, pg=dict(domains=domains)),
                partitions=[dict(name="p0", type="a", origin_um=[0.0, 0.0]),
                            dict(name="p1", type="a", origin_um=[400.0, 0.0], orient="MY")],
                partition_types=dict(a=t), ports=[], lanes=[])


def _ov(a, o):
    return min(a[2], o[2]) > max(a[0], o[0]) + 1e-6 and min(a[3], o[3]) > max(a[1], o[1]) + 1e-6


def test_phy_supply_rects_type_frame_union():
    # p1 is mirrored (MY): its die-frame domain [410, 40, 800, 300] maps back to the same type-frame rect
    P = S.Plan(_plan([dict(name="phy0", nets=["VDDPHY", "VSS"], rect_um=PHY),
                      dict(name="phy1", nets=["VDDPHY", "VSS"], rect_um=[410.0, 40.0, 800.0, 300.0])]))
    assert CP.phy_supply_rects(P, "a") == [PHY]
    assert CP.phy_supply_rects(S.Plan(_plan([])), "a") == []


def test_band_avoids_the_phy_supply_region():
    legacy = CP._storage_band(_type(), "rx_i", 1, [])
    assert _ov(legacy["rect_um"], PHY)             # the macro-only search lands inside the supply region (the bug)
    b = CP._storage_band(_type(), "rx_i", 1, [], phy=[PHY])
    assert not _ov(b["rect_um"], PHY)
    assert b["max_pin_to_band_hop_um"] <= 405 - 2.16
    assert b["phy_supply_blockage_um"] == [PHY]


def test_band_clear_of_the_region_is_byte_identical():
    far = [0.0, 40.0, 200.0, 300.0]
    assert CP._storage_band(_type(), "rx_i", 1, [], phy=[far]) == CP._storage_band(_type(), "rx_i", 1, [])
    assert CP._storage_band(_type(), "rx_i", 1, [], phy=[]) == CP._storage_band(_type(), "rx_i", 1, [])


def _resize_case(domains):
    p = _plan(domains)
    t = p["partition_types"]["a"]
    CP.BAND_RESERVE = "ring_ff"
    try:
        tt = _type()
        band = CP._storage_band(tt, "rx_i", 1, [])
    finally:
        CP.BAND_RESERVE = "padded"
    t["clock"]["landing_contract"]["bands"]["rx_i"] = dict(band, instance="u_cland_rx_i")
    side = dict(collector=dict(types=dict(a=dict(bus_geometry=GEOM))))
    return p, side


def test_resize_moves_a_full_size_band_out_of_the_region():
    p, side = _resize_case([dict(name="phy0", nets=["VDDPHY", "VSS"], rect_um=PHY)])
    old = p["partition_types"]["a"]["clock"]["landing_contract"]["bands"]["rx_i"]
    assert _ov(old["rect_um"], PHY)
    new, rep = CP.resize_undersized_bands(p, side, ["a"])
    b = new["partition_types"]["a"]["clock"]["landing_contract"]["bands"]["rx_i"]
    assert not _ov(b["rect_um"], PHY) and b["resized_from_um"] == old["rect_um"]
    assert "PHY supply-region" in b["resize"] and [r["bus"] for r in rep] == ["rx_i"]
    assert CP.BAND_RESERVE == "padded"


def test_resize_without_a_region_is_byte_identical():
    p, side = _resize_case([])
    new, rep = CP.resize_undersized_bands(p, side, ["a"])
    assert new == p and rep == []


# ---- landing_placement.tcl: fail closed on a ring band over a hard blockage ------------------------------------------
LP_TCL = HERE / "landing_placement.tcl"
MOCK = r"""
proc mk {o props} { set ::P($o) $props; proc $o {m args} [string map [list @O@ $o] { return [dict get $::P(@O@) $m] }] }
mk bbx {xMin @X0@ yMin 50000 xMax 120000 yMax 60000}
mk bk {getBBox bbx isSoft @SOFT@}
mk blk {getInsts {} getBlockages {bk}}
set ff_blk blk; set ff_dbu 1000
set ff_x0 0; set ff_y0 0; set ff_x1 200000; set ff_y1 200000; set ff_rh 270; set ff_sw 54
set ff_orient {}
set ::env(RESULTS_DIR) @RES@
@AVOID@
set cland_groups {{u_cland_rx_i {100.0 40.0 110.0 80.0} ring:rx_i}}
set cland_optional_groups {}
set cland_status {}
source @LP@
"""


def _lp(tmp_path, x0, soft=0, avoid=""):
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh not installed")
    s = (MOCK.replace("@X0@", str(x0)).replace("@SOFT@", str(soft)).replace("@RES@", str(tmp_path))
         .replace("@AVOID@", avoid).replace("@LP@", str(LP_TCL)))
    f = tmp_path / "lp_mock.tcl"
    f.write_text(s)
    return subprocess.run(["tclsh", str(f)], capture_output=True, text=True)


def test_ring_band_over_hard_blockage_fails_closed(tmp_path):
    r = _lp(tmp_path, 105000)
    assert r.returncode != 0 and "overlaps hard placement blockage" in r.stderr, r.stderr


def test_ring_band_clear_soft_or_packed_around_passes_the_check(tmp_path):
    # past the check, the empty mock netlist stops at the existing "no mapped cells" error
    for kw in (dict(x0=110000), dict(x0=105000, soft=1),
               dict(x0=105000, avoid="set ::cland_avoid_rects {{105000 50000 120000 60000}}")):
        r = _lp(tmp_path, **kw)
        assert r.returncode != 0 and "no mapped cells found under u_cland_rx_i" in r.stderr, (kw, r.stderr)
