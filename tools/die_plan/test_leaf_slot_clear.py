"""leaf_slot_clear (S81-LEAF-T14 11-15): the ve_m / ve_s slot reader and the in-macro station-site reader."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import leaf_slot_clear as LS  # noqa: E402


def macro(inst, x, y, w, h):
    return dict(inst=inst, lef="x.lef", origin_um=[x, y], outline_um=[w, h], orient="R0")


def ttype(sites):
    return dict(outline_um=[600.0, 600.0],
                contents=[macro("u_lf.u_ve.u_s", 40.0, 40.0, 170.0, 340.0), macro("u_lf.u_ve.u_m", 218.64, 40.0, 170.0, 340.0)],
                ft_slots=[dict(name="ft0", bit_site_cell_um=[2.16, 0.27], bit_sites_um=[sites])])


def test_in_macro_counts_sites_inside_a_core():
    t = ttype([[100.0, 100.0], [212.0, 100.0], [300.0, 100.0]])      # 1st in ve_s, 2nd in the slot, 3rd in ve_m
    out = LS.in_macro(t)
    assert out[0][0] == "ft0" and out[0][2] == 2 and out[0][3] == 3


def test_ve_slot_reads_gap_sites_and_push_direction():
    t = ttype([[210.0, 100.0], [212.0, 120.0], [300.0, 100.0]])
    gap, n, axis, sign = LS.ve_slot_sites(t, LS.S.placed_macro_boxes(t))
    assert abs(gap - 8.64) < 1e-6 and n == 2 and axis == 0 and sign == 1       # ve_m east of ve_s -> push east
