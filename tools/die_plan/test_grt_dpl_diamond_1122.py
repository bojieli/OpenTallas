"""GRT-DPL-DIAMOND-1122 (COORD 23:0x, FAM-QC-SLWSLE-R1 DPL-0033): the GRT stage's post-repair detailed_placement honours the
kit's diamond legalizer args (captured before ORFS erases them), and a non-diamond pass that leaves an illegal placement gets one
diamond pass."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WRAP = ROOT / "physical/common_flow/grt183_make.sh"
GRT_ORFS = ("utl::set_metrics_stage \"globalroute__{}\"\nerase_non_stage_variables grt\nproc global_route_helper { } {\n"
            "  source_step_tcl PRE GLOBAL_ROUTE\n  log_cmd detailed_placement\n  source_step_tcl POST GLOBAL_ROUTE\n}\n")
KIT = "-use_diamond_legalizer -max_displacement {614 1340}"


def wrap(tmp, cfg=""):
    w, s = tmp / "work", tmp / "scripts"
    w.mkdir()
    s.mkdir()
    (w / "config.mk").write_text(cfg)
    (s / "global_route.tcl").write_text(GRT_ORFS)
    e = dict(os.environ, OT_GRT183_WORK=str(w), OT_GRT183_SCRIPTS=str(s), OT_GRT183_RESUME="0")
    for _ in range(2):                                                   # idempotent per container
        p = subprocess.run(["bash", str(WRAP), "true"], env=e, capture_output=True, text=True)
        assert p.returncode == 0, p.stdout + p.stderr
    return s


def test_wrapper_captures_before_erase_once(tmp_path):
    c = (wrap(tmp_path) / "global_route.tcl").read_text().splitlines()
    i = c.index("erase_non_stage_variables grt")
    assert c[i - 1].startswith("set ::ot_grt_dpl_args ") and c[i - 1].endswith(";# OT_GRT_DPL_ARGS")
    assert sum("OT_GRT_DPL_ARGS" in x for x in c) == 1


def test_opt_out(tmp_path):
    assert "OT_GRT_DPL_ARGS" not in (wrap(tmp_path, "export OT_GRT_DPL_ARGS = 0\n") / "global_route.tcl").read_text()


@pytest.mark.parametrize("kit,illegal,want", [
    (KIT, 0, ["dpl " + KIT, "dpl -max_displacement {5 1}", "check_placement"]),
    ("", 0, ["dpl", "check_placement", "dpl -max_displacement {5 1}", "check_placement"]),
    ("", 1, ["dpl", "check_placement", "dpl -use_diamond_legalizer", "dpl -max_displacement {5 1}", "check_placement"]),
    ("-disallow_one_site_gaps", 1, ["dpl", "check_placement", "dpl -use_diamond_legalizer", "dpl -max_displacement {5 1}",
                                    "check_placement"]),
])
def test_line_behaviour(tmp_path, kit, illegal, want):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    line = next(x for x in (wrap(tmp_path) / "global_route.tcl").read_text().splitlines() if "OT_GRT_DPL_ARGS" in x)
    t = tmp_path / "l.tcl"
    t.write_text("set ::log {}\nset ::bad %d\nproc detailed_placement {args} { lappend ::log [string trim \"dpl $args\"] }\n"
                 "proc check_placement {args} { lappend ::log check_placement; if {$::bad} { set ::bad 0; error DPL-0033 } }\n"
                 % illegal + line + "\narray unset ::env DETAIL_PLACEMENT_ARGS\n"
                 "detailed_placement\ndetailed_placement -max_displacement {5 1}\nputs LOG=[join $::log |]\n")
    e = {k: v for k, v in os.environ.items() if k != "DETAIL_PLACEMENT_ARGS"}
    if kit:
        e["DETAIL_PLACEMENT_ARGS"] = kit
    p = subprocess.run(["tclsh", str(t)], env=e, capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
    log = [x for x in p.stdout.splitlines() if x.startswith("LOG=")][0][4:].split("|")
    assert log == want, log
    assert ("OT_GRT_DPL_ARGS residual" in p.stdout) == bool(illegal)
