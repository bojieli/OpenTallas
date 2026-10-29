"""gen_phys clock.reserved_sites_um (FALLBACK-HEAD-2, opt-in)."""
from types import SimpleNamespace as N
import pytest
import gen_phys as GP


def plan(rows):
    t = dict(outline_um=[100, 50], clock={} if rows is None else dict(reserved_sites_um=rows))
    return N(types={"T": t})


def test_absent_key_emits_nothing():
    assert GP.reserved_sites_tcl(plan(None), "T") == ("", "", "")


def test_tree_sites_are_hard_and_ring_banks_are_gpl_only():
    pre, post, rel = GP.reserved_sites_tcl(plan([dict(rect_um=[1, 2, 3, 4], kind="die_clock_tree"),
                                                 dict(rect_um=[10, 20, 30, 25], kind="landing_ring_bank", ref="u_cland_i")]), "T")
    assert "odb::dbBlockage_create $rs_b [expr {round(1*$rs_u)}] [expr {round(2*$rs_u)}]" in pre
    assert "ot_clear_keepout_physical $rs_b $rs_rects reserved_die_clock_tree" in pre
    assert "set ::cland_avoid_rects $rs_rects" in pre
    assert "round(10*$rs_u)" not in pre and "round(1*$rs_u)" not in post
    assert "lappend ::rs_bank $rs_k" in post and "rects=1" in post
    assert "odb::dbBlockage_destroy $rs_k" in rel and "of 1 ring-bank blockages" in rel


def test_tree_hole_inside_a_bank_is_allowed():
    pre, post, _ = GP.reserved_sites_tcl(plan([dict(rect_um=[12, 21, 14, 22], kind="die_clock_tree"),
                                               dict(rect_um=[10, 20, 30, 25], kind="landing_ring_bank")]), "T")
    assert pre and post


@pytest.mark.parametrize("row,msg", [(dict(rect_um=[90, 0, 101, 5], kind="die_clock_tree"), "outside"),
                                     (dict(rect_um=[5, 5, 5, 6], kind="die_clock_tree"), "outside"),
                                     (dict(rect_um=[1, 1, 2, 2], kind="keepout"), "kind")])
def test_bad_rows_fail_closed(row, msg):
    with pytest.raises(ValueError, match=msg):
        GP.reserved_sites_tcl(plan([row]), "T")


def test_landing_placement_avoid_is_opt_in():
    from pathlib import Path
    t = Path(GP.__file__).with_name("landing_placement.tcl").read_text()
    assert "if {[info exists ::cland_avoid_rects]}" in t


def test_bank_release_finds_blockages_in_the_odb_not_a_tcl_variable():
    # DIE-HEAD-14: GPL (3_3) and DPL (3_5) are separate OpenROAD processes; ::rs_bank does not survive between them
    _, _, rel = GP.reserved_sites_tcl(plan([dict(rect_um=[10, 20, 30, 25], kind="landing_ring_bank"),
                                           dict(rect_um=[40, 20, 60, 25.5], kind="landing_ring_bank")]), "T")
    assert "::rs_bank" not in rel and "getBlockages" in rel
    assert "[list [expr {round(10*$rs_u)}] [expr {round(20*$rs_u)}] [expr {round(30*$rs_u)}] [expr {round(25*$rs_u)}]]" in rel
    assert "[expr {round(25.5*$rs_u)}]]" in rel
    assert "if {$rs_n != 2}" in rel and "of 2 ring-bank blockages" in rel
