"""FABLE-PD-KV-1450 fix 5 (COORD r167): -congestion_iterations 15 on the incremental global_route of kits with head_eighth cores (the
repair_antennas allow-congestion wrapper is already on main, df791a048f)."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402

SH = HERE.parents[1] / "physical" / "common_flow" / "grt183_make.sh"
TCLSH = shutil.which("tclsh")


def test_cfg_only_for_head_eighth_types():
    assert gen_phys.grt_cong_iter_cfg({}) == []
    assert gen_phys.grt_cong_iter_cfg({"hard_cores": [dict(inst="u_a", module="ot_dp_x")]}) == []
    cfg = gen_phys.grt_cong_iter_cfg({"hard_cores": [dict(inst="u_a", module="ot_dp_x"), dict(inst="u_h", module="kv3_head_eighth_a")]})
    assert cfg[-1] == "export OT_GRT_CONG_ITER = 15"
    assert gen_phys.grt_cong_iter_cfg({"hard_cores": [dict(inst="u_kv3_head_eighth_1", module="m")]}) != []


def test_repair_antennas_stays_in_the_allow_congestion_wrapper():
    t = SH.read_text()
    assert "foreach c {repair_timing repair_design repair_antennas}" in t


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_wrapper_adds_the_bound_to_every_global_route_only_with_the_variable(tmp_path):
    t = SH.read_text()
    tcl = t[t.index("<<'OT_AC_TCL'\n") + len("<<'OT_AC_TCL'\n"):t.index("\nOT_AC_TCL\n")]
    stub = ("namespace eval ::grt { proc set_allow_congestion {v} {} }\n"
            "proc ::global_route {args} { set ::last $args }\nproc ::repair_timing {args} {}\nproc ::repair_design {args} {}\nproc ::repair_antennas {args} {}\n")
    drv = lambda env: (stub + env + tcl + "\nglobal_route -end_incremental -congestion_iterations 7\nputs [set ::last]\nglobal_route -start_incremental\nputs [set ::last]\n")
    (tmp_path / "a.tcl").write_text(drv('set ::env(OT_GRT_CONG_ITER) 15\n'))
    out = subprocess.run([TCLSH, str(tmp_path / "a.tcl")], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    lines = [l for l in out.stdout.splitlines() if l.startswith("-")]
    assert lines[0] == "-end_incremental -congestion_iterations 7 -allow_congestion"          # an explicit bound is kept
    assert lines[1] == "-start_incremental -allow_congestion -congestion_iterations 15"
    (tmp_path / "b.tcl").write_text(drv(""))
    out = subprocess.run([TCLSH, str(tmp_path / "b.tcl")], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert [l for l in out.stdout.splitlines() if l.startswith("-")][1] == "-start_incremental -allow_congestion"
