"""DIE-S81-50 11-03: stale-staging check (prd_spef_insts.py + prd_hook.tcl ot_prd_stage_check) and the clock-tree
cell data-pin class (ICG ENA dont_touch -> RSZ-3006) in prd_hook.tcl."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import prd_spef_insts as P  # noqa: E402

SPEF = """*SPEF "ieee 1481-1999"
*DIVIDER /
*DELIMITER :

*NAME_MAP
*1 A32\\[0\\]
*2 A32\\[0\\]\\$_DFF_P_
*3 hxeco_1_n2
*4 ANTENNA_7

*PORTS
*1 I

*D_NET *1 0.001
*CONN
*P *1 I
*I *2:D I *D DFFHQNx1_ASAP7_75t_R
*I *3:A I *D HB1xp67_ASAP7_75t_R
*I *4:A I *D ANTENNA_ASAP7_75t_R
*I u7:Y O *D INVx1_ASAP7_75t_R
*END
"""


def test_spef_instances_resolve_name_map_and_skip_physical():
    ins = P.instances(SPEF.splitlines(True))
    assert ins == {"A32\\[0\\]\\$_DFF_P_": "DFFHQNx1_ASAP7_75t_R", "hxeco_1_n2": "HB1xp67_ASAP7_75t_R",
                   "u7": "INVx1_ASAP7_75t_R"}


def _stage_proc():
    t = (HERE / "prd_hook.tcl").read_text()
    m = re.search(r"^proc ot_prd_stage_check .*?^}\n", t, re.S | re.M)
    assert m
    return m.group(0)


@pytest.mark.skipif(not shutil.which("tclsh"), reason="tclsh")
@pytest.mark.parametrize("db,ok", [(["A32[0]$_DFF_P_", "hxeco_1_n2", "u7"], True), (["A32[0]$_DFF_P_", "u7"], False)])
def test_stage_check_in_tcl(tmp_path, db, ok):
    lst = tmp_path / "l.tsv"
    lst.write_text("".join(f"{i} {m}\n" for i, m in sorted(P.instances(SPEF.splitlines(True)).items())))
    names = " ".join("{" + n + "}" for n in db)
    script = f"""
namespace eval ord {{}}
proc ord::get_db_block {{}} {{ return blk }}
set ::db [list {names}]
proc blk {{op name}} {{ if {{$name in $::db}} {{ return inst }} ; return NULL }}
{_stage_proc()}
if {{[catch {{ot_prd_stage_check {lst}}} msg]}} {{ puts "ERR $msg"; exit 1 }}
puts OK
"""
    p = subprocess.run(["tclsh"], input=script, capture_output=True, text=True)
    assert (p.returncode == 0) == ok, p.stdout + p.stderr
    if not ok:
        assert "OT_PRD STAGE_MISMATCH: 1 of 3" in p.stdout and "hxeco_1_n2" in p.stdout


def test_hook_order_and_clock_cell_data_pins():
    t = (HERE / "prd_hook.tcl").read_text()
    # the stage check runs before the routed SPEF is read; fillers of a final seed go first
    assert t.index("remove_fillers") < t.index("ot_prd_stage_check /work/prd_spef_insts.tsv") \
        < t.index("ot_prd_spef_arm $::env(RESULTS_DIR)/6_final.spef\n  set _ckf")
    # ICG data pins: dont_touch off after the freeze, before the sink-family dont_use (so the ICG family is dont_use),
    # restored before the master revert guard and legalization
    i_off = t.index("$inst setDoNotTouch 0")
    assert t.index("ot_clk_freeze\n}") < i_off < t.index("set ::ot_prd_masters [ot_prd_clock_insts]")
    i_res = t.index("ot_prd_dtoff_restore\nset ::ot_prd_reverted")
    assert t.index("repair_timing -hold {*}$args") < i_res < t.index("\ndetailed_placement\n")
    assert 'OT_PRD_CLKCELL_DATA_PINS) ne "0"' in t
    # route-keeping for route and final seeds
    assert '$::env(OT_PRD_FROM) in {route final}' in t


def test_prd_mk_final_seed_and_list():
    t = (HERE / "prd_mk.sh").read_text()
    assert "final) SRC=6_final.odb" in t and 'prd_spef_insts.py" "$SPEF" $OUT/prd_spef_insts.tsv' in t
    r = (HERE / "prd_run.sh").read_text()
    assert "= final ] && OT_PRD_FROM=route" in r


# HBM-FORM-SPLIT-12 11-06: yosys merged-register names carry a literal backslash; SPEF escapes it (\\), OpenDB keeps
# it escaped too but leaves . and $ bare (Q2NF helpers: 2322 false STAGE_MISMATCH misses).  A truly absent instance
# must still stop the ECO.
SPEF_MERGED = r"""*NAME_MAP
*1 u_x\._7_\[0\]\$\\u_x\._7_\[1\]\$dff\[0\]\$_DFF_P_

*D_NET *9 0.001
*CONN
*I *1:D I *D DFFHQNx1_ASAP7_75t_R
*I u_y\._8_\[2\]\$\\u_y\._8_\[3\]\$dff\[1\]\$_DFF_P_:D I *D DFFHQNx1_ASAP7_75t_R
*END
"""
MERGED_DB = [r"u_x._7_\[0\]$\\u_x._7_\[1\]$dff\[0\]$_DFF_P_", r"u_y._8_\[2\]$\\u_y._8_\[3\]$dff\[1\]$_DFF_P_"]


@pytest.mark.skipif(not shutil.which("tclsh"), reason="tclsh")
@pytest.mark.parametrize("db,ok", [(MERGED_DB, True), (MERGED_DB[:1], False)])
def test_stage_check_merged_backslash_names(tmp_path, db, ok):
    ins = P.instances(SPEF_MERGED.splitlines(True))
    assert len(ins) == 2
    lst = tmp_path / "l.tsv"
    lst.write_text("".join(f"{i} {m}\n" for i, m in sorted(ins.items())))
    names = " ".join("{" + n + "}" for n in db)
    script = f"""
namespace eval ord {{}}
proc ord::get_db_block {{}} {{ return blk }}
set ::db [list {names}]
proc blk {{op name}} {{ if {{$name in $::db}} {{ return inst }} ; return NULL }}
{_stage_proc()}
if {{[catch {{ot_prd_stage_check {lst}}} msg]}} {{ puts "ERR $msg"; exit 1 }}
puts OK
"""
    p = subprocess.run(["tclsh"], input=script, capture_output=True, text=True)
    assert (p.returncode == 0) == ok, p.stdout + p.stderr
    if not ok:
        assert "OT_PRD STAGE_MISMATCH: 1 of 2" in p.stdout and "u_y" in p.stdout


# DIE-S81-82 11-08: hierarchical kit names (t51 vD).  SPEF escapes the dots and the divider; OpenDB leaves the dots
# bare and keeps \/ (58218 of 116412 false STAGE_MISMATCH).  A truly absent instance must still stop the ECO.
SPEF_HIER = r"""*NAME_MAP
*1 u_bound\.u_x\/_4_

*D_NET *9 0.001
*CONN
*I *1:A I *D INVx1_ASAP7_75t_R
*I u_bound\.u_y\/r\[3\]\$_DFF_P_:D I *D DFFHQNx1_ASAP7_75t_R
*END
"""
HIER_DB = [r"u_bound.u_x\/_4_", r"u_bound.u_y\/r\[3\]$_DFF_P_"]


@pytest.mark.skipif(not shutil.which("tclsh"), reason="tclsh")
@pytest.mark.parametrize("db,ok", [(HIER_DB, True), (HIER_DB[:1], False)])
def test_stage_check_hierarchical_divider_names(tmp_path, db, ok):
    ins = P.instances(SPEF_HIER.splitlines(True))
    assert len(ins) == 2
    lst = tmp_path / "l.tsv"
    lst.write_text("".join(f"{i} {m}\n" for i, m in sorted(ins.items())))
    names = " ".join("{" + n + "}" for n in db)
    script = f"""
namespace eval ord {{}}
proc ord::get_db_block {{}} {{ return blk }}
set ::db [list {names}]
proc blk {{op name}} {{ if {{$name in $::db}} {{ return inst }} ; return NULL }}
{_stage_proc()}
if {{[catch {{ot_prd_stage_check {lst}}} msg]}} {{ puts "ERR $msg"; exit 1 }}
puts OK
"""
    p = subprocess.run(["tclsh"], input=script, capture_output=True, text=True)
    assert (p.returncode == 0) == ok, p.stdout + p.stderr
