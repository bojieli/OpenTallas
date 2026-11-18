"""FABLE-FIX-QC-STA 11-18: a single-stage tail copy fed by a hard macro sits at a fraction of the source -> pin route."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SRC = Path(__file__).with_name("tail_copy_anchor.tcl").read_text()
needs_tclsh = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh")


def proc(name):
    m = re.search(r"^proc " + re.escape(name) + r"\s+\{[^\n]*?\}\s+\{", SRC, re.M)
    i, d = m.end(), 1
    while d:
        c = SRC[i]
        i += 1
        if c == "\\":
            i += 1
            continue
        d += (c == "{") - (c == "}")
    return SRC[m.start():i]


@needs_tclsh
def test_fraction_point_follows_the_bends_of_the_route(tmp_path):
    f = tmp_path / "t.tcl"
    f.write_text(proc("tcs_md") + "\n" + proc("tcs_frac") + """
set r {1000 0 {0 0} {300 0} {300 700}}
foreach x {0 0.3 0.6 1} { puts [tcs_frac $r $x] }
""")
    out = subprocess.run(["tclsh", str(f)], capture_output=True, text=True, check=True).stdout.splitlines()
    assert out == ["0 0", "300 0", "300 300", "300 700"]


def test_hook_sites_macro_fed_single_stage_copies_off_the_pin():
    assert "tcs_macro_src [tcs_dnet [lindex $chain 0]]" in SRC and "OT_TAIL_SRC_FRAC" in SRC
    assert "[[$di getMaster] isBlock]" in proc("tcs_macro_src")
