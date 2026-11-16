"""Repair progress is advisory; no cancellation or repair bypass on a quiet log."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from test_grt183_kit import calls, fake, kit, run

HERE = Path(__file__).resolve().parent
TCL = HERE / "grt_maxwire.tcl"
FAST = {"OT_GRT_REPAIR_STALL_S": "3", "OT_GRT_REPAIR_LOG_S": "1", "OT_GRT_STALL_POLL": "1", "OT_GRT_STALL_KILL_WAIT": "1"}
ROW = "     4000 |     +0.0%% |       0 |    1232 |          1116 |    142176"
IN_REPAIR = ('if [ $N = 1 ]; then printf "OT_MAXWIRE repair_design -verbose -max_wire_length 100\\n%s\\n" > $L/5_1_grt.tmp.log; '
             'sleep 60; exit 0; fi\n' % ROW)
OK2 = 'ls $R > $K/ls$N.txt; echo ok > $L/5_1_grt.log; exit 0\n'


def test_flat_repair_logs_without_cancellation_or_rerun(tmp_path):
    k, r, l, s = kit(tmp_path)
    p = run(k, s, fake(tmp_path, IN_REPAIR.replace("sleep 60", "sleep 6")), "grt", env=FAST)
    assert p.returncode == 0, p.stdout + p.stderr
    assert len(calls(k)) == 1
    assert "OT_GRT_REPAIR_PASS post-GRT repair_design nets_done=4000 buffers=1232 remaining=142176" in p.stdout
    assert "OT_GRT_REPAIR_NO_PROGRESS" not in p.stdout
    assert not (r / "5_1_grt.repair_nostall.json").exists()
    assert (r / "4_cts.odb").read_text() == "cts"


def test_finished_repair_or_other_step_is_not_stopped(tmp_path):
    done = IN_REPAIR.replace('\\n" >', '\\nOT_MAXWIRE leaf instances 1 -> 2\\n" >').replace("sleep 60", "sleep 6")
    k, r, l, s = kit(tmp_path)
    p = run(k, s, fake(tmp_path, done), "grt", env=FAST)
    assert p.returncode == 0 and len(calls(k)) == 1 and "OT_GRT_REPAIR_" not in p.stdout


def test_opt_out(tmp_path):
    for how in ("env", "config"):
        k, r, l, s = kit(tmp_path / how, "export OT_GRT_REPAIR_STALL_S = 0\n" if how == "config" else "")
        env = dict(FAST, **({"OT_GRT_REPAIR_STALL_S": "0"} if how == "env" else {}))
        if how == "config":
            env.pop("OT_GRT_REPAIR_STALL_S")
        p = run(k, s, fake(tmp_path / how, IN_REPAIR.replace("sleep 60", "sleep 6")), "grt", env=env)
        assert p.returncode == 0 and len(calls(k)) == 1 and "OT_GRT_REPAIR_NO_PROGRESS" not in p.stdout, how


STUBS = r"""
set ::env(OT_MAXWIRE_UM) 100
set ::env(RESULTS_DIR) [lindex $argv 0]
set ::n 7
proc log_cmd {args} { puts "LOG [join $args { }]"; if {[lindex $args 0] eq "repair_design"} { incr ::n 5 } }
proc check_placement {args} { puts CHECK }
namespace eval sta { proc network_leaf_instance_count {} { return $::n } }
proc repair_design_helper {} { puts ORIG_BASE }
"""
needs_tclsh = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def tcl(tmp_path, env=None, pre=""):
    t = tmp_path / "t.tcl"
    t.write_text(STUBS + pre + f"source {TCL}\nputs HOOK_END\nrepair_design_helper\n")
    import os
    return subprocess.run(["tclsh", str(t), str(tmp_path)], capture_output=True, text=True, check=True,
                          env=dict(os.environ, **(env or {}))).stdout


@needs_tclsh
def test_default_is_post_pass_only_with_pass_line(tmp_path):
    pre, post = tcl(tmp_path).split("HOOK_END")
    assert "repair_design" not in pre
    assert "OT_MAXWIRE repair_design" in post and "OT_MAXWIRE leaf instances 7 -> 12" in post
    assert "OT_MAXWIRE_PASS post done: +5 cells" in post


@needs_tclsh
def test_opt_in_pitch_pass_runs_before_global_route(tmp_path):
    pre, post = tcl(tmp_path, env={"OT_MAXWIRE_PRE": "1"}).split("HOOK_END")
    assert pre.index("LOG estimate_parasitics -placement") < pre.index("LOG repair_design -verbose -max_wire_length 100") \
        < pre.index("LOG detailed_placement") < pre.index("CHECK")
    assert "OT_MAXWIRE_PASS pre done: +5 cells" in pre and "OT_MAXWIRE_PASS post done: +5 cells" in post


@needs_tclsh
def test_legacy_marker_cannot_skip_post_repair(tmp_path):
    (tmp_path / "5_1_grt.repair_nostall.json").write_text("{}")
    pre, post = tcl(tmp_path).split("HOOK_END")
    assert "repair_design" not in pre
    assert "OT_MAXWIRE_PASS post skipped" not in post and "LOG repair_design" in post
