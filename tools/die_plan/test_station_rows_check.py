"""QC-PLAN-R3 (COORD 11-20, FABLE-PD-QC-2300 F1/F2): station_rows_check finds rows kit_istations refuses and exact bit
sites inside hard cores before an event is applied."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import station_rows_check as SRC  # noqa: E402

W = 2


def t_of(rows, cores=()):
    return dict(buses=[dict(name="x", dir="in", width=W)], internal_stations=rows, hard_cores=list(cores))


def test_exact_sites_with_bit_route_is_a_form_finding():
    row = dict(conn="bus:x", regs_um=[[10, 10]], bit_sites_um=[[[1, 1], [2, 1], [3, 1]]], bit_site_cell_um=[1.404, 0.27],
               bit_route="per_bit", leaf_um=[5, 5])
    kinds = [k for k, _, _ in SRC.row_findings("t", t_of([row]))]
    assert "FORM" in kinds


def test_per_bit_without_leaf():
    row = dict(conn="bus:x", regs_um=[[10, 10]], bit_route="per_bit")
    assert [k for k, _, _ in SRC.row_findings("t", t_of([row]))] == ["LEAF"]


def test_bit_site_inside_hard_core_halo():
    core = dict(inst="u_r0", origin_um=[0, 0], outline_um=[20, 20], halo_um=2)
    row = dict(conn="bus:x", regs_um=[[30, 30]], bit_sites_um=[[[21, 5], [25, 5], [40, 40]]], bit_site_cell_um=[1.404, 0.27])
    f = [x for x in SRC.row_findings("t", t_of([row], [core])) if x[0] == "INSIDE"]
    assert len(f) == 1 and f[0][2].startswith("1 bit sites inside u_r0")


def test_clean_per_bit_row():
    row = dict(conn="bus:x", regs_um=[[10, 10]], bit_route="per_bit", leaf_um=[5, 5])
    assert SRC.row_findings("t", t_of([row])) == []
