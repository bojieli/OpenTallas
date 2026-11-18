"""KV-Q2-CLK-1115 CTS-TAP-CENTROID: opt-in clock branch-buffer centroid hook (cts_tap_centroid.tcl), its cts_post wiring and gen_phys export."""
import shutil
import subprocess
from pathlib import Path

import pytest

D = Path(__file__).resolve().parent
TCL = (D / "cts_tap_centroid.tcl").read_text()


def test_hook_only_moves_branch_buffers_and_never_edits_connectivity():
    # branch buffers only: clkbuf_<lvl>_<n>_<m>_ with lvl >= 1 (root clkbuf_0, leaves clkbuf_leaf_*, macro branch clkbuf_N_N__f_ untouched)
    assert r"^clkbuf_([0-9]+)_[0-9]+_[0-9]+_" in TCL and "$lvl >= 1" in TCL
    # placement only: no cell creation / net edits / disconnects
    for bad in ("dbInst_create", "dbNet_create", "disconnect", "destroy"):
        assert bad not in TCL


def test_hook_skips_macros_and_is_bottom_up_and_reportable():
    assert "isBlock" in TCL and "skip_macro" in TCL                      # centre on a macro (+4 um halo): not moved
    assert "lsort -integer -decreasing -index 0" in TCL                  # level descending = bottom-up
    assert "OT_TAP_REPORT_ONLY" in TCL and "OT_TAP_UM" in TCL
    assert "detailed_placement" in TCL and "check_placement" in TCL      # re-legalised after the moves
    assert "string match clkload*" in TCL                                # dummy loads follow, never set the centre


def test_cts_post_sources_it_only_when_opted_in():
    post = (D / "cts_post.tcl").read_text()
    line = [l for l in post.splitlines() if "cts_tap_centroid.tcl" in l and "source" in l]
    assert len(line) == 1
    assert 'OT_CTS_TAP_CENTROID) eq "1"' in line[0] and "file exists" in line[0]
    # after leaf_affinity, before the reset pair placement
    assert post.index("leaf_affinity.tcl") < post.index("cts_tap_centroid.tcl") < post.index("reset_pair_place.tcl")


def test_gen_phys_copies_file_and_exports_only_when_env_set():
    src = (D / "gen_phys.py").read_text()
    assert src.count('"cts_tap_centroid.tcl"') == 1                      # copied into every kit (inert without the env)
    line = [l for l in src.splitlines() if "export OT_CTS_TAP_CENTROID = 1" in l]
    assert len(line) == 1
    assert 'os.environ.get("OT_CTS_TAP_CENTROID", "").strip() == "1"' in line[0]


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_tcl_parses():
    prog = "set f [open %s]\nset s [read $f]\nputs [info complete $s]\n" % (D / "cts_tap_centroid.tcl")
    r = subprocess.run(["tclsh"], input=prog, capture_output=True, text=True)
    assert r.stdout.strip() == "1", r.stdout + r.stderr
