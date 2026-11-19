"""CTS-POST-RPT-1: CTS-stage timing is re-reported after the POST_CTS hooks (ORFS writes 4_cts_final.rpt before them)."""
import shutil
import subprocess
from pathlib import Path

import pytest

D = Path(__file__).resolve().parent


def test_cts_post_sources_report_last():
    body = (D / "cts_post.tcl").read_text().rstrip().splitlines()
    assert "cts_post_report.tcl" in body[-1]
    tb = next(i for i, l in enumerate(body) if "tap_balance.tcl" in l)
    assert tb < len(body) - 1


def test_report_is_copied_into_kits():
    src = (D / "gen_phys.py").read_text()
    assert chr(34).join(['', 'cts_post.tcl', ', ', 'cts_post_report.tcl', '']) in src


def test_report_has_no_netlist_edits():
    t = (D / "cts_post_report.tcl").read_text()
    for cmd in ("insert_buffer", "repair_", "make_inst", "connect_pin", "disconnect", "remove_buffers", "detailed_placement"):
        assert cmd not in t
    assert "OT_CTS_POST_TIMING" in t and "4_cts_post_hook.rpt" in t


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="no tclsh")
def test_tcl_parses():
    r = subprocess.run(["tclsh"], input="set f [open %s]; set s [read $f]; puts [info complete $s]" % (D / "cts_post_report.tcl"),
                       capture_output=True, text=True)
    assert r.stdout.strip() == "1"
