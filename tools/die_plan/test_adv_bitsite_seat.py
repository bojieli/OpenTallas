"""pytest: ADV-BITSITE-SEAT (KV A5t2 RREACH: 39 entries up to 659 um off; in-core 3 patterns ~40 um off)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_bitsite_seat as A  # noqa: E402


def slot(sites, regs, stations=3):
    return {"name": "ft0", "width": 1, "stations": stations, "regs_um": regs, "bit_site_cell_um": [1.404, 0.27], "bit_sites_um": sites}


def test_seated_slot_passes_and_moved_station_flags():
    ok = slot([[[100.0, 100.0], [100.0, 100.27]], [[200.0, 100.0], [200.0, 100.27]]], [[0, 0], [101.0, 100.0], [201.0, 100.0]])
    assert A.check_ft(ok, 10.0) is None
    moved = slot(ok["bit_sites_um"], [[0, 0], [101.0, 100.0], [201.0, 759.0]])        # 659 um off (A5t2 RREACH)
    r = A.check_ft(moved, 10.0)
    assert r[0] == "SEAT" and r[1][0][0] == 1 and r[1][0][1] > 600


def test_wrong_stage_count_is_count_error():
    bad = slot([[[100.0, 100.0], [100.0, 100.27]]], [[0, 0], [101.0, 100.0], [201.0, 100.0]])      # 1 stage for 3 stations
    assert A.check_ft(bad, 10.0)[0] == "COUNT"


def test_incore_row_stage_count_and_seat():
    row = {"conn": "bus:o", "regs_um": [[10.0, 10.0], [50.0, 10.0]], "bit_sites_um": [[[10.0, 10.0]], [[90.0, 10.0]]]}
    r = A.check_row(row, 10.0)
    assert r[0] == "SEAT" and r[1][0][0] == 1 and round(r[1][0][1]) == 40
    assert A.check_row({"conn": "bus:o", "regs_um": [[1, 1]] * 5, "bit_sites_um": [[[1, 1]]]}, 10.0)[0] == "COUNT"


def test_never_raises():
    assert A.findings(None, "p")[0].startswith("WARN ADV-BITSITE-SEAT not checked")
