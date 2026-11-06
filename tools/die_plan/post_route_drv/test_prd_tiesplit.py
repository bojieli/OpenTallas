import pathlib
import shutil
import subprocess

import pytest

HERE = pathlib.Path(__file__).parent


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_split_off_mark_dirty_runs_with_empty_list():
    script = r"""
namespace eval ord {proc get_db_block {} {return block}}
set ::env(OT_PRD_TIE_SPLIT) 0
source [lindex $argv 0]
ot_prd_tie_mark_dirty
"""
    r = subprocess.run(["tclsh", "/dev/stdin", str(HERE / "prd_tiesplit.tcl")], input=script,
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
    assert "tie nets marked dirty 0, recreated 0" in r.stdout
