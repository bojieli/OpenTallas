"""tail_copy_anchor.tcl moves copy stages another hook already made FIRM instead of dying on ODB-0359 (FABLE-FIX-KV-HG 11-18)."""
import os, re
S = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tail_copy_anchor.tcl")).read()


def test_every_move_releases_first():
    moves = re.findall(r"^.*\$cell setLocation .*$", S, re.M)
    assert len(moves) >= 2
    for ln in moves:
        assert ln.index("tcs_unfix $cell") < ln.index("$cell setLocation"), ln
        assert "setPlacementStatus FIRM" in ln


def test_unfix_only_touches_fixed_cells_and_reports():
    m = re.search(r"proc tcs_unfix \{cell\} \{\n(.*?)\n\}", S, re.S)
    assert m and "in {FIRM LOCKED}" in m.group(1) and "setPlacementStatus PLACED" in m.group(1)
    assert "OT_TAIL_SITE re-sited $::tcs_refix" in S
