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


CELL = [1.404, 0.27]


def row_at(conn, x, y, dx=0.0):
    return dict(conn=conn, regs_um=[[10, 10]], bit_sites_um=[[[x + dx * i, y] for i in range(W + 1)]], bit_site_cell_um=CELL)


def test_two_rows_claiming_the_same_sites_overlap():
    # FABLE-PD-QC-1600 (QC st_a rs_s0 / rs_s1): same sites in two rows passed gen and failed at global_place
    a, b = row_at("bus:x", 50, 50, 2.0), row_at("bus:x", 50, 50, 2.0)
    f = [x for x in SRC.row_findings("t", t_of([a, b])) if x[0] == "OVERLAP"]
    assert len(f) >= 1 and "#0" in f[0][1] and "#1" in f[0][1]


def test_a_partial_overlap_is_found_and_adjacent_rows_are_clean():
    a = row_at("bus:x", 50, 50, 2.0)
    shifted = row_at("bus:x", 50.7, 50.1, 2.0)                      # overlaps in x and y by part of a cell
    assert [x[0] for x in SRC.row_findings("t", t_of([a, shifted]))].count("OVERLAP") >= 1
    touching = row_at("bus:x", 50, 50.27, 2.0)                      # next row up, edges touch only
    assert [x for x in SRC.row_findings("t", t_of([a, touching])) if x[0] == "OVERLAP"] == []
    far = row_at("bus:x", 80, 50, 2.0)
    assert [x for x in SRC.row_findings("t", t_of([a, far])) if x[0] == "OVERLAP"] == []


def test_cross_row_function_ignores_overlap_inside_one_row():
    import kit_istations as KI
    one = ("a", [[[1, 1], [1.2, 1]]], (1.404, 0.27))                # overlaps itself: packed_exact_geometry's job, not this check
    assert KI.cross_row_site_overlaps([one]) == []
    two = ("b", [[[1.5, 1.1]]], (1.404, 0.27))
    assert KI.cross_row_site_overlaps([one, two])[0][:2] in (("a", "b"), ("b", "a"))
