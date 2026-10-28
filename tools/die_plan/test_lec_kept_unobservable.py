"""FLOW-GEN-1 10-28 (QC-A0-KITS-4, romleaf 688f9c1b2571): post-route LEC 3316/3316 proved, but KEEP FAIL 32 of 1206:
ORFS eliminate_dead_logic removed kept flops no compare point observes (xa_m[8k+7] only reach a shift that drops
them).  A kept bit outside the gold AIG cone of every compare point (po: / bb:) is reported as unobservable_removed,
not failed; an observed kept bit that is absent still FAILs (mutant).
python3 -m pytest -q tools/die_plan/test_lec_kept_unobservable.py"""
import lec
from test_lec import _seq


def _design(tmp_path, cp1_observed):
    keep = tmp_path / "gold.keep"
    keep.write_text("lec_top/u_dut.cp\n")
    lat = ["cp[0]", "cp[1]", "dead2", "u_bb.lec_bbi_o"]
    g, gm = _seq(tmp_path, "g", ["d"], lat,
                 lambda m, l: {"cp[0]": l["d"], "cp[1]": l["d"] ^ 1, "dead2": l["cp[1]"],     # cp[1] -> dead2 -> -
                               "u_bb.lec_bbi_o": m.XOR(l["cp[0]"], l["cp[1]"] if cp1_observed else l["d"])})
    t, tm = _seq(tmp_path, "t", ["d"], ["cp[0]", "u_bb.lec_bbi_o"],
                 lambda m, l: {"cp[0]": l["d"], "u_bb.lec_bbi_o": m.XOR(l["cp[0]"], l["d"])})
    return lec.Lec(g, gm, t, tm), keep


def test_unobservable_kept_bit_is_reported_not_failed(tmp_path):
    L, keep = _design(tmp_path, False)
    assert lec.unobservable_keys(L) == {"ff:u_dut.cp[1]", "ff:u_dut.dead2"}
    declared, missing, const = lec.kept_registers(L, keep)
    assert declared == ["ff:u_dut.cp[0]", "ff:u_dut.cp[1]"] and not missing and not const
    assert L.kept_unobservable == ["ff:u_dut.cp[1]"]


def test_observed_kept_bit_removed_still_fails(tmp_path):
    L, keep = _design(tmp_path, True)       # mutant: cp[1] reaches the compare point, so its absence is a FAIL
    assert lec.unobservable_keys(L) == {"ff:u_dut.dead2"}
    assert lec.kept_registers(L, keep)[1] == ["ff:u_dut.cp[1]"] and L.kept_unobservable == []


def test_no_compare_point_exempts_nothing(tmp_path):
    keep = tmp_path / "gold.keep"
    keep.write_text("lec_top/u_dut.cp\n")
    g, gm = _seq(tmp_path, "g", ["d"], ["cp[0]", "cp[1]"], lambda m, l: {"cp[0]": l["d"], "cp[1]": l["d"]})
    t, tm = _seq(tmp_path, "t", ["d"], ["cp[0]"], lambda m, l: {"cp[0]": l["d"]})
    L = lec.Lec(g, gm, t, tm)
    assert lec.unobservable_keys(L) == set() and lec.kept_registers(L, keep)[1] == ["ff:u_dut.cp[1]"]
