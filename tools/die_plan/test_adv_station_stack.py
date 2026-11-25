"""pytest: ADV-STATION-STACK (KV-OWN-PV V1NSITE class: parallel buses with identical station points)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_station_stack as A  # noqa: E402


def typ(d1_regs, tap=(1641.6, 138.24)):
    return {"buses": [{"name": "vo", "width": 269}, {"name": "vo_d1", "width": 269}, {"name": "vo_d2", "width": 269}],
            "internal_stations": [
                {"conn": "bus:vo", "regs_um": [[1640.0, 140.0], [520.0, 1400.0]]},
                {"conn": "bus:vo", "regs_um": [[1640.0, 140.0], [520.0, 1400.0]]},      # one entry listed twice: one bus
                {"conn": "bus:vo_d1", "regs_um": d1_regs},
                {"conn": "bus:vo_d2", "regs_um": [[1640.04, 140.0], [520.0, 1400.0]]}],
            "reset": {"local_taps_um": [list(tap)]},
            "clock": {"landing_reader_start": {"branches": {"b": {"stages": [{"xy_um": [523.0, 1400.22]}]}}}}}


def test_three_bus_stack_with_tap_and_start():
    r = A.judge_type(typ([[1640.0, 140.0], [520.0, 1400.0]]))
    assert (r["points"], r["ft"], r["max_buses"], r["max_bits"], r["tap"], r["start"]) == (2, 0, 3, 807, 1, 1)


def test_ft_slot_stack_counted_apart():
    t = typ([[1652.0, 140.0], [532.0, 1400.0]]); t["internal_stations"] = t["internal_stations"][:1]
    t["ft_slots"] = [{"name": "ft4", "width": 1, "regs_um": [[520.0, 1400.0]]}]
    r = A.judge_type(t)
    assert (r["points"], r["ft"], r["max_bits"]) == (1, 1, 270)


def test_spread_buses_clean_and_same_bus_duplicate_not_a_stack():
    t = typ([[1652.0, 140.0], [532.0, 1400.0]])
    t["internal_stations"][3]["regs_um"] = [[1628.0, 140.0], [508.0, 1400.0]]
    assert A.judge_type(t)["points"] == 0


def test_findings_summary_and_never_raises():
    ls = A.findings({"partition_types": {"kv3_pv_v1n": typ([[1640.0, 140.0], [520.0, 1400.0]]), "h": {"hard": True}}}, "p")
    assert ls[0].startswith("WARN ADV-STATION-STACK kv3_pv_v1n: 2 station point(s)") and "1 of 1 soft types" in ls[-1]
    assert A.findings(None, "p")[0].startswith("WARN ADV-STATION-STACK not checked")


def test_core_net_bits_field():
    t = {"internal_stations": [{"conn": "core:a|core:b", "bits": "1", "regs_um": [[10.0, 10.0]]},
                               {"conn": "core:a|core:c", "bits": 2, "regs_um": [[10.0, 10.0]]}]}
    assert A.judge_type(t)["max_bits"] == 3
