"""CLAND-BIN 11-15 (kv3_hub_Wo OT_CLAND BAND FAIL on two literal-local-reset windows): LAND-RESERVE defaults on for kits that have such bands."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TCL = (Path(__file__).resolve().parent / "face_flops.tcl").read_text()
pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def _proc():
    return re.search(r"^proc ff_land_reserve_default \{path\} \{\n.*?\n\}\n", TCL, re.S | re.M).group(0)


def _run(tmp_path, groups, env=None, missing=False):
    f = tmp_path / "landing_placement.tcl"
    if not missing:
        f.write_text("set cland_groups {\n" + groups + "\n}\nset cland_status {\n  {n 1 2}\n}\n# literal-local-reset in a comment below the list\n")
    pre = "" if env is None else "set ::env(OT_LAND_RESERVE) %s\n" % env
    body = pre + _proc() + "puts [ff_land_reserve_default %s]\nputs [expr {[info exists ::env(OT_LAND_RESERVE)] ? $::env(OT_LAND_RESERVE) : {unset}}]\n" % f
    return subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split("\n")[-3:-1]


def test_default_on_when_a_literal_local_reset_band_exists(tmp_path):
    assert _run(tmp_path, "  {u_cland_raw_x {1 2 3 4} literal-local-reset}") == ["1", "1"]


def test_unchanged_without_such_a_band(tmp_path):
    assert _run(tmp_path, "  {u_cland_x {1 2 3 4} ring:a+ff}") == ["0", "unset"]


def test_explicit_zero_and_one_are_respected(tmp_path):
    assert _run(tmp_path, "  {u_cland_raw_x {1 2 3 4} literal-local-reset}", env="0") == ["0", "0"]
    assert _run(tmp_path, "  {u_cland_raw_x {1 2 3 4} literal-local-reset}", env="1") == ["0", "1"]


def test_no_landing_file_is_a_no_op(tmp_path):
    assert _run(tmp_path, "", missing=True) == ["0", "unset"]


def test_runs_before_the_reserve_block_and_the_landing_hook_reads_the_same_env():
    assert TCL.index("ff_land_reserve_default /work/landing_placement.tcl") < TCL.index('$::env(OT_LAND_RESERVE) eq "1"} {\n  set ff_lr_fh')
