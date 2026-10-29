"""HBM-CORES-KITS-20: OT_F4_PAIR is opt-in; the default F4 path (head-leaf rule) is unchanged."""
from pathlib import Path

F4 = Path(__file__).with_name("f4_chain_leaf.tcl").read_text()


def test_pair_mode_is_opt_in():
    assert 'if {[info exists ::env(OT_F4_PAIR)] && $::env(OT_F4_PAIR)} {' in F4


def test_pair_mode_keeps_bounds():
    blk = F4[F4.index("OT_F4_PAIR)] && $::env(OT_F4_PAIR)"):F4.index("OT_F4 PAIR pairs")]
    assert "$::f4_um * $dbu" in blk and "$::f4_add" in blk   # same distance / leaf-growth bounds as the head rule
    assert "$cc connect $pn" in blk                          # capture joins its own launch leaf


def test_default_path_unchanged():
    assert "if {$size($h) + 1 > $::f4_max} { incr skipped; continue }" in F4
    assert 'puts "OT_F4 pairs [array size pred] moved $moved skipped $skipped far $far' in F4
