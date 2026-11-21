"""KV-032 class (FAM-KV-IOPC-R3 11-21): tt_setup_repair.tcl releases a FIRM cell the repair upsized in place onto a fixed neighbour
for its detailed_placement and re-FIRMs it after; kv3_io_cor_v1 u_cland_ft5_i sd_c[81] DFFLQNx1 -> x2 over sd_c[219], DPL-0033 at 5_3."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parent
TCLSH = shutil.which("tclsh")
SRC = (BASE / "tt_setup_repair.tcl").read_text()


def _procs():
    return "\n".join(re.search(r"^proc ::%s \{.*?^\}" % n, SRC, re.S | re.M).group(0)
                     for n in ("ot_firm_widths", "ot_firm_grown_release", "ot_firm_grown_refirm"))


def _run(cells, grow):
    """cells: (name, status, x0, width, row_y); grow: {index: new width} applied between the snapshot and the release"""
    mock = _procs() + r'''
proc blk {method} {return $::insts}
proc inst {id method args} {
 switch $method {
  getName {return $::nm($id)}
  getMaster {return m$id}
  getBBox {return b$id}
  getPlacementStatus {return $::state($id)}
  setPlacementStatus {set ::state($id) [lindex $args 0]}
 }
}
proc mst {id method} { switch $method { isBlock {return 0} getWidth {return $::w($id)} } }
proc bbox {id method} { switch $method { yMin {return $::y($id)} xMin {return $::x0($id)} xMax {return [expr {$::x0($id) + $::w($id)}]} } }
'''
    for i, (n, st, x0, w, y) in enumerate(cells):
        mock += (f"set nm({i}) {{{n}}}\nset state({i}) {st}\nset x0({i}) {x0}\nset w({i}) {w}\nset y({i}) {y}\n"
                 f"interp alias {{}} c{i} {{}} inst {i}\ninterp alias {{}} m{i} {{}} mst {i}\ninterp alias {{}} b{i} {{}} bbox {i}\nlappend insts c{i}\n")
    mock += "set snap [::ot_firm_widths blk]\n"
    for i, w in grow.items():
        mock += f"set w({i}) {w}\n"
    ids = range(len(cells))
    mock += ("set rel [::ot_firm_grown_release blk $snap]\nputs \"MID " + " ".join(f"$state({i})" for i in ids) + "\"\n"
             "::ot_firm_grown_refirm $rel\nputs \"END " + " ".join(f"$state({i})" for i in ids) + "\"\n")
    p = subprocess.run([TCLSH], input=mock, text=True, capture_output=True)
    assert p.returncode == 0, p.stderr
    return p.stdout


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_upsized_firm_ring_flop_over_its_firm_neighbour_is_released_then_refirmed():
    # io_cor_v1: sd_c[81] at 1119.258 (x1 1.080 um = 20 sites of 54) abuts sd_c[219] at 1120.338; x2 is 1.134 um
    cells = [("u_cland_ft5_i/sd_c[81]", "FIRM", 1119258, 1080, 434700), ("u_cland_ft5_i/sd_c[219]", "FIRM", 1120338, 1080, 434700),
             ("TAP_1", "FIXED", 1130000, 54, 434700), ("u_cland_ft5_i/sd_c[7]", "FIRM", 1119258, 1080, 434970)]
    out = _run(cells, {0: 1134})
    assert "MID PLACED FIRM FIXED FIRM" in out, out
    assert "END FIRM FIRM FIXED FIRM" in out, out
    assert "OT_FIRM_GROWN released 1 FIRM cells" in out and "re-FIRMed 1 cells" in out


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_legal_kit_and_an_upsize_that_still_fits_are_unchanged():
    cells = [("a", "FIRM", 0, 1080, 0), ("b", "FIRM", 2000, 1080, 0), ("TAP", "FIXED", 4000, 54, 0)]
    out = _run(cells, {0: 1134})          # x2 ends at 1134 < 2000: still legal
    assert "MID FIRM FIRM FIXED" in out and "OT_FIRM_GROWN released 0 FIRM cells" in out, out
    assert "re-FIRMed" not in out


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_only_the_grown_cell_moves_never_its_neighbour_or_a_placed_cell():
    # neighbour 'b' was not resized; 'p' is movable (DPL moves it anyway); the grown cell 'a' overlaps a TAPCELL
    cells = [("b", "FIRM", 0, 1080, 0), ("a", "FIRM", 1080, 1080, 0), ("TAP", "FIXED", 2160, 54, 0), ("p", "PLACED", 1100, 500, 0)]
    out = _run(cells, {1: 1134})
    assert "MID FIRM PLACED FIXED PLACED" in out, out
    assert "END FIRM FIRM FIXED PLACED" in out, out


def test_release_wraps_the_post_repair_dpl():
    blk = SRC[SRC.index("ot_bounded_repair tt_setup_repair"):]
    i_rel, i_dpl, i_re = (blk.index(k) for k in ("::ot_firm_grown_release", "detailed_placement", "::ot_firm_grown_refirm"))
    assert i_rel < i_dpl < i_re
    assert SRC.index("set ot_fw [::ot_firm_widths") < SRC.index("ot_bounded_repair tt_setup_repair [list")
