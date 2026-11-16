"""DRT0255-PROOF-1115 finding (k_t49: DPL-0004 'Placed in rows check failed (3861)' on TAP cells with OT_PG_CELL_KEEPOUT=1): the keepout
blockages must skip crossings that lie over fixed cells.  Pure-Tcl helpers run with tclsh."""
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCLSH = shutil.which("tclsh")


def _proc(name):
    t = (HERE / "pg_cell_keepout.tcl").read_text()
    i = t.index(f"proc {name} ")
    for open_n in (1, 2):                      # argument list, then body
        k = t.index("{", i if open_n == 1 else j)
        depth = 0
        for j in range(k, len(t)):
            depth += t[j] == "{"
            depth -= t[j] == "}"
            if depth == 0:
                break
    return t[i:j + 1]


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_crossings_over_fixed_cells_are_dropped_the_rest_kept():
    src = "\n".join(_proc(n) for n in ("ot_pgcko_index", "ot_pgcko_box_hit", "ot_pgcko_drop_covered"))
    script = src + """
set xs {{100 100 300 700} {5000 100 5200 700} {9000 9000 9200 9600}}
set tap {{250 0 1650 270} {8000 0 9400 270}}
lassign [ot_pgcko_drop_covered $xs $tap] kept dropped
puts $dropped; puts [llength $kept]; puts [lindex $kept 0]; puts [lindex $kept 1]
lassign [ot_pgcko_drop_covered $xs {}] k2 d2
puts "$d2 [llength $k2]"
"""
    out = subprocess.run([TCLSH], input=script, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split("\n")[:5] == ["1", "2", "5000 100 5200 700", "9000 9000 9200 9600", "0 3"]


def test_add_creates_blockages_only_after_the_fixed_cell_filter():
    t = (HERE / "pg_cell_keepout.tcl").read_text()
    assert t.index("[ot_pgcko_drop_covered $xs [ot_pgcko_fixed_boxes $blk]]") < t.index("odb::dbBlockage_create $blk $x0 $y0 $x1 $y1")
    assert "CORE_TAPCELL*" in t and "FIXED LOCKED FIRM COVER" in t
