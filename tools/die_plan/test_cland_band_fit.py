"""DIE-KV-80/PLAN 11-05 CLAND-BAND: a band a hard core overlaps is re-sited clear of it; free bands never move."""
import copy
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cland_band_fit as F  # noqa: E402


def _plan():
    t = dict(outline_um=[600.0, 400.0], buses=[], ft_slots=[],
             hard_cores=[dict(inst="u_core", module="m", origin_um=[51.84, 25.92], outline_um=[216.0, 211.68])],
             clock=dict(landing_contract=dict(
                 pins=[dict(name="cland_dn_ready_0", xy_um=[163.488, 2.656])],
                 bands=dict(monitor_0=dict(rect_um=[247.698, 28.08, 273.618, 36.72], width=2, instance="u_cland_monitor_0"),
                            free_1=dict(rect_um=[400.14, 100.08, 426.06, 108.72], width=2)))))
    return dict(partition_types=dict(tA=t), partitions=[])


def test_blocked_band_moves_clear_and_free_band_stays():
    raw = _plan()
    out, rep = F.run(raw, None)
    assert [m["bus"] for m in rep["moved"]] == ["monitor_0"] and not rep["failed"]
    b = out["partition_types"]["tA"]["clock"]["landing_contract"]["bands"]
    core = (51.84, 25.92, 267.84, 237.6)
    nr = b["monitor_0"]["rect_um"]
    assert not F.ov(nr, core) and nr[0] >= core[2] + 4.32 - 1e-6           # off the core and its reset clearance
    assert abs(F.area(nr) - F.area([247.698, 28.08, 273.618, 36.72])) < 0.5   # same size
    assert F.area(nr) >= 1.25 * F.model_reserve(2)
    assert b["monitor_0"]["resited_from_um"] == [247.698, 28.08, 273.618, 36.72]
    assert b["free_1"] == raw["partition_types"]["tA"]["clock"]["landing_contract"]["bands"]["free_1"]
    assert rep["moved"][0]["hop_um"] <= F.REACH


def test_no_overlap_no_change():
    raw = _plan()
    raw["partition_types"]["tA"]["hard_cores"][0]["origin_um"] = [21.6, 60.0]
    out, rep = F.run(copy.deepcopy(raw), None)
    assert out == raw and not rep["moved"]


def test_blocked_but_enough_free_area_is_reported_not_moved():
    raw = _plan()
    raw["partition_types"]["tA"]["hard_cores"][0]["outline_um"] = [196.0, 211.68]   # covers 0.0 of the band
    raw["partition_types"]["tA"]["hard_cores"][0]["origin_um"] = [53.0, 25.92]     # right edge 249.0: tiny overlap
    out, rep = F.run(copy.deepcopy(raw), None)
    assert not rep["moved"] and len(rep["blocked_not_moved"]) == 1 and out == raw


def _hard_plan():
    """QC cbn_q00 form: the ring band is the footprint of the hard cland child that implements it (RING-SPLIT-1106)."""
    t = dict(outline_um=[600.0, 400.0], buses=[], ft_slots=[],
             hard_cores=[dict(inst="cl_bc_i00", module="ot_cland_bc", origin_um=[436.32, 17.28],
                              outline_um=[89.184, 51.84], track_offset_um=[0.012, 0.012])],
             clock=dict(landing_contract=dict(bands=dict(bc_i00=dict(
                 rect_um=[436.32, 17.28, 525.504, 69.12], width=516, instance="u_cland_bc_i00", hard_core="cl_bc_i00",
                 max_pin_to_band_hop_um=113.712)))))
    return dict(partition_types=dict(tA=t), partitions=[])


def test_hard_child_band_is_checked_not_failed_or_moved():
    raw = _hard_plan()
    for check in (True, False):
        out, rep = F.run(copy.deepcopy(raw), None, check=check)
        assert out == raw and not rep["failed"] and not rep["moved"] and not rep["blocked_not_moved"]
        assert [(h["bus"], h["hard_core"], h["others"]) for h in rep["hard_child"]] == [("bc_i00", "cl_bc_i00", [])]


def test_hard_child_band_without_its_child_or_off_its_child_fails():
    raw = _hard_plan()
    raw["partition_types"]["tA"]["hard_cores"][0]["inst"] = "cl_other"
    _, rep = F.run(copy.deepcopy(raw), None, check=True)
    assert not rep["hard_child"] and len(rep["failed"]) == 1      # band now under a foreign macro, its child absent
    raw = _hard_plan()
    raw["partition_types"]["tA"]["hard_cores"][0]["origin_um"] = [440.64, 17.28]
    _, rep = F.run(copy.deepcopy(raw), None, check=True)
    assert len(rep["failed"]) == 1 and "is not the band" in rep["failed"][0]["error"]


def test_hard_child_band_under_another_macro_or_out_of_reach_fails():
    raw = _hard_plan()
    raw["partition_types"]["tA"]["hard_cores"].append(dict(inst="u_sram", module="m", origin_um=[500.0, 60.0],
                                                           outline_um=[50.0, 50.0]))
    _, rep = F.run(copy.deepcopy(raw), None, check=True)
    assert len(rep["failed"]) == 1 and "overlaps ['u_sram']" in rep["failed"][0]["error"]
    raw = _hard_plan()
    raw["partition_types"]["tA"]["clock"]["landing_contract"]["bands"]["bc_i00"]["max_pin_to_band_hop_um"] = 410.0
    _, rep = F.run(copy.deepcopy(raw), None, check=True)
    assert len(rep["failed"]) == 1 and "pin hop" in rep["failed"][0]["error"]
