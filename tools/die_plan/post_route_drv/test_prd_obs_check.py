"""S81-COL-PRD-OBS 11-17 (FABLE-PD-S81-0720 B1): the prd (post-route ECO) path must remove the temporary PG-track GRT obstructions
before 5_1_grt.odb is written and fail before detail route when the per-layer obstruction counts differ from the seed's."""
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
CHECK = HERE / "prd_obs_check.tcl"


def test_eco_post_removes_temporary_obstructions_then_checks_before_write():
    mk = (HERE / "prd_mk.sh").read_text()
    a = mk.index("ot_pgtt_remove")
    b = mk.index("ot_pgcko_remove")
    c = mk.index("ot_prd_obs_check")
    assert mk.index("source /work/prd_post_grt_chain.tcl") < a < b < c < mk.index("source /work/pg_connect.tcl") < mk.index("> $OUT/eco_post.tcl")
    assert "cp --remove-destination $HERE/prd_obs_check.tcl $OUT/" in mk          # staged into the kit with the other hooks


def test_seed_is_taken_before_anything_is_added():
    pre = (HERE / "eco_grt_pre.tcl").read_text()
    assert pre.index("ot_prd_obs_seed") < pre.index("OT_ECO_GRT_PRE_CHAIN")


MOCK = r'''
set OBS {}
proc obs_add {layer n} { global OBS; for {set i 0} {$i < $n} {incr i} { lappend OBS $layer } }
namespace eval ord {}
proc ord::get_db_block {} { return blk }
proc blk {op} { global OBS; if {$op eq "getObstructions"} { set r {}; foreach l $OBS { lappend r "obs_$l" }; return $r } }
proc bbox_of {o} { return "bb_[string range $o 4 end]" }
foreach l {M5 M6 M7 M8} {
  proc obs_$l {op} "if {\$op eq \"getBBox\"} { return bb_$l }"
  proc bb_$l {op} "if {\$op eq \"getTechLayer\"} { return ly_$l }"
  proc ly_$l {op} "if {\$op eq \"getName\"} { return $l }"
}
'''


def _run(body):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    src = MOCK + "\nsource {" + str(CHECK) + "}\nif {[catch {\n" + body + "\n} e]} { puts \"CAUGHT $e\"; exit 1 }\n"
    r = subprocess.run(["tclsh"], input=src, text=True, capture_output=True)
    return r.returncode, r.stdout + r.stderr


def test_check_passes_when_temporary_obstructions_were_removed():
    rc, out = _run("obs_add M8 3\not_prd_obs_seed\nobs_add M5 5\nset OBS [lsearch -all -inline -not $OBS M5]\not_prd_obs_check\n")
    assert rc == 0 and "OT_PRD_OBS_CHECK PASS" in out, out


def test_check_fails_before_drt_when_obstructions_are_left_in():
    # the col pg3 repair: seed M8 only, 2896 M5 + 740 M6 + 331 M7 temporary ones left in 5_1_grt.odb
    rc, out = _run("obs_add M8 3\not_prd_obs_seed\nobs_add M5 7\nobs_add M6 4\nobs_add M7 2\not_prd_obs_check\n")
    assert rc != 0 and "OT_PRD_OBS_CHECK FAIL" in out and "M5 seed 0 allowed +0 now 7" in out and "M6 seed 0" in out and "M7 seed 0" in out, out


def test_allow_list_and_off_switch():
    rc, out = _run("obs_add M8 3\not_prd_obs_seed\nobs_add M5 1\nset ::env(OT_PRD_OBS_ALLOW) {M5=1}\not_prd_obs_check\n")
    assert rc == 0 and "PASS" in out, out
    rc, out = _run("obs_add M8 3\not_prd_obs_seed\nobs_add M5 9\nset ::env(OT_PRD_OBS_CHECK) 0\not_prd_obs_check\n")
    assert rc == 0 and "skipped" in out, out


def test_missing_seed_fails_closed():
    rc, out = _run("obs_add M8 3\not_prd_obs_check\n")
    assert rc != 0 and "no seed" in out, out
