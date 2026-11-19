"""NS-BANK-FALLBACK 11-19 (FABLE-FIX-S81-LEAF): a face register with no comb cell (row stride > 1) inside the pin retention takes a
stride-1 cell instead of stopping the kit; stride 1 kits walk the search once, as before.
    python3 -m pytest -q tools/die_plan/test_face_ns_fallback.py"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TCL = (Path(__file__).resolve().parent / "face_flops.tcl").read_text()


def test_fallback_is_in_the_ns_bank_search_only():
    body = TCL[TCL.index("proc ff_put_near {f x y} {"):TCL.index("# interior pin registers")]
    assert "foreach ff_try_stride [expr {$ff_ns_stride > 1 ? [list $ff_ns_stride 1] : [list $ff_ns_stride]}]" in body
    assert "%$ff_try_stride ||" in body and "%$ff_ns_stride ||" not in body
    assert body.index("foreach ff_try_stride") < body.index('error "NS face bank cannot fit')    # the stop stays, after both passes
    assert body.count("OT_FACE_FLOPS NS bank fallback") == 1


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="no tclsh")
def test_stride_list(tmp_path):
    expr = re.search(r"foreach ff_try_stride (\[expr \{.*?\}\])", TCL).group(1)
    out = subprocess.run(["tclsh"], input=f"foreach s {{1 2 4}} {{ set ff_ns_stride $s; puts {expr} }}\n", capture_output=True, text=True).stdout.split("\n")
    assert out[:3] == ["1", "2 1", "4 1"]


def test_wide_column_pass_is_last_and_keeps_the_retention():
    """NS-BANK-WIDE: the 3 pin columns first (both strides), then up to 12 columns either side at stride 1, same 27-um retention."""
    body = TCL[TCL.index("proc ff_put_near {f x y} {"):TCL.index("# interior pin registers")]
    wide = body.index("foreach ff_try_cols [list {0 1 -1} {2 -2 3 -3")
    assert wide < body.index("foreach ff_try_stride") < body.index("foreach dc $ff_try_cols") < body.index('error "NS face bank cannot fit')
    assert "foreach dc {0 1 -1}" not in body[wide:body.index('error "NS face bank cannot fit')]
    assert "if {[llength $ff_try_cols] > 3 && $ff_ns_stride > 1 && $ff_try_stride != 1} continue" in body
    assert body.count(">27*$ff_dbu} continue") >= 1 and body.count("OT_FACE_FLOPS NS bank wide") == 1


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="no tclsh")
def test_ns_search_parses_and_orders_passes():
    """the three nested loops are balanced Tcl and visit (cols, stride) as: 3 cols comb, 3 cols full, wide full"""
    body = TCL[TCL.index("    foreach ff_try_cols [list"):TCL.index('    error "NS face bank cannot fit')]
    head = body[:body.index("    for {set depth $ff_ns_inset}")]
    prog = "set ff_ns_stride 2\n" + head + '    puts "[llength $ff_try_cols] $ff_try_stride"\n    }\n    }\n'
    out = subprocess.run(["tclsh"], input=prog, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split("\n")[:3] == ["3 2", "3 1", "22 1"]
