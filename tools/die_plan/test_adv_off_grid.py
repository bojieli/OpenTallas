"""ADV-OFF-GRID: KV sys_c row C (FAM-KV-HUBC-SYSC-R2 a6fb0ce2baf0) R-DOB o_dcal_dob exact bank sites off the 0.054 grid."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_off_grid as O  # noqa: E402

# real values from the failing plan (post_C6 faeeae1b2122): kv3_sys_c outline 2160 x 1036.8, CORE_AREA inset 4.32
BAD = [[[1107.192, 985.5], [1108.596, 985.5], [1879.092, 985.5], [1111.404, 985.5]]]


def _snap(x):
    return round(round((x - 4.32) / 0.054) * 0.054 + 4.32, 3)


def plan(sites):
    return {"partition_types": {"kv3_sys_c": {
        "outline_um": [2160.0, 1036.8],
        "internal_stations": [{"conn": "bus:o_dcal_dob", "bit_sites_um": sites, "bit_site_cell_um": [1.404, 0.27]}],
        "relay_sites": {"u_x/q": [100.001, 100.0]},
        "hard_cores": [{"inst": "u_m", "origin_um": [14.736, 100.0], "outline_um": [10, 10]}]}}}


def test_positive_flagged():
    out = O.findings(plan(BAD), "p.json")
    hit = [ln for ln in out if ln.startswith("WARN ADV-OFF-GRID kv3_sys_c: EXACT")]
    assert hit and "bus:o_dcal_dob" in hit[0] and "(1111.4,985.5) x" in hit[0]
    assert " 3 exact" in hit[0]          # 1879.092 is on the grid ((1879.092 - 4.32) / 0.054 = 34718)


def test_snapped_clean():
    good = [[[_snap(x), y] for x, y in st] for st in BAD]
    out = O.findings(plan(good), "p.json")
    assert not any(": EXACT" in ln for ln in out)
    assert any("summary" in ln and "0 EXACT" in ln and "1 MACRO" in ln and "1 CELL" in ln for ln in out)


def test_off_row_and_outside():
    assert O.off_grid(4.32 + 0.054 * 10, 4.32 + 0.1, [4.32, 4.32, 100, 100]) == (False, True)
    assert O.off_grid(1.0, 50.0, [4.32, 4.32, 100, 100]) is None      # outside CORE_AREA: ADV-BANK-OFFAREA's


def test_never_raises():
    assert O.findings({"partition_types": {"t": {"outline_um": "bad"}}}, "p")[0].startswith("WARN ADV-OFF-GRID")
