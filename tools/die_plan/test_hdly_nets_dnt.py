"""C-HOLDCHAIN-NET-NOT-DNT (COORD FABLE-RC-S81 1247): the nets feeding dont_touch u_hdly_ HB4 pad cells are dont_touch before GPL.

Runs the REAL face_flops.tcl proc ff_hdly_nets_dnt in tclsh against a mocked OpenDB (a 3-stage chain u_hdly_ft8_i.g_b[995].g_k[0..2].u_hb
with inter-stage nets c[k]) and checks the kit gen_lint check hdly_nets_dnt.
    python3 -m pytest -q tools/die_plan/test_hdly_nets_dnt.py"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SRC = (HERE / "face_flops.tcl").read_text()
sys.path.insert(0, str(HERE))
import kit_gen_lint as GL  # noqa: E402


def _proc():
    i = SRC.index("proc ff_hdly_nets_dnt {}")
    return SRC[i:SRC.index("\nff_hdly_nets_dnt\n", i)]


MOCK = r"""
namespace eval ord { proc get_db_block {} { return blk } }
array set dnt {}
proc blk {m} { global insts; return $insts }
proc inst {n m args} { global dnt pins
  switch -- $m { getName { return $n } isDoNotTouch { return [info exists dnt($n)] } getITerms { return $pins($n) } } }
proc iterm {inp net m} { switch -- $m { isInputSignal { return $inp } getNet { return $net } } }
proc net {n sig m args} { global dnt
  switch -- $m { getSigType { return $sig } isDoNotTouch { return [info exists dnt($n)] } setDoNotTouch { set dnt($n) 1 } getName { return $n } } }
set insts {}
proc mk {name isdnt ins} { global insts dnt pins
  interp alias {} $name {} inst $name; lappend insts $name; if {$isdnt} { set dnt($name) 1 }
  set l {}; foreach {inp nname sig} $ins { interp alias {} N_$nname {} net $nname $sig; interp alias {} IT_${name}_$nname {} iterm $inp N_$nname; lappend l IT_${name}_$nname }
  set pins($name) $l }
"""


def _run(extra, env=""):
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    script = env + MOCK + _proc() + "\n" + extra
    r = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, timeout=60)
    return r


CHAIN = ("mk {u_hdly_ft8_i.g_b[995].g_k[0].u_hb} 1 {1 bus SIGNAL 0 q0 SIGNAL}\n"
         "mk {u_hdly_ft8_i.g_b[995].g_k[1].u_hb} 1 {1 c1 SIGNAL 0 q1 SIGNAL}\n"
         "mk {u_hdly_ft8_i.g_b[995].g_k[2].u_hb} 1 {1 c2 SIGNAL 0 q2 SIGNAL}\n"
         "mk u_other.buf 0 {1 other SIGNAL}\n"
         "mk u_hdly_lk_x.pad 0 {1 lknet SIGNAL}\n"
         "mk u_hdly_clkpad 1 {1 clknet CLOCK}\n")


def test_chain_nets_become_dont_touch_and_others_do_not():
    r = _run(CHAIN + "ff_hdly_nets_dnt\nputs [join [lsort [array names dnt]] ,]")
    assert r.returncode == 0 and not r.stderr, r.stdout + r.stderr
    assert "OT_HDLY_NETS_DNT pads=4 nets_marked=3 missing=0" in r.stdout, r.stdout
    marked = r.stdout.strip().splitlines()[-1].split(",")
    for n in ("bus", "c1", "c2"):
        assert n in marked
    assert "other" not in marked and "lknet" not in marked and "clknet" not in marked   # non-dnt cells and clock nets untouched


def test_idempotent_second_run_marks_nothing():
    r = _run(CHAIN + "ff_hdly_nets_dnt\nff_hdly_nets_dnt")
    assert "nets_marked=3 missing=0" in r.stdout and "nets_marked=0 missing=0" in r.stdout, r.stdout


def test_env_zero_restores_the_old_flow():
    r = _run(CHAIN + "ff_hdly_nets_dnt\nputs [array size dnt]", env="set ::env(OT_HDLY_NETS_DNT) 0\n")
    assert "off (OT_HDLY_NETS_DNT=0)" in r.stdout and r.stdout.strip().splitlines()[-1] == "4", r.stdout   # only the 4 dnt instances


def test_pass_runs_before_global_placement_in_the_hook():
    i = SRC.index("\nff_hdly_nets_dnt\n")
    assert i < SRC.index("set ff_core_boxes {}\nif {![info exists ::env(OT_FF_CORE_SKIP)]")
    assert i < SRC.index("proc ff_put_near")


def _kit(tmp_path, pre, face, cfg="export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl\n"):
    (tmp_path / "config.mk").write_text(cfg)
    if pre is not None:
        (tmp_path / "pre_floorplan_type.tcl").write_text(pre)
    if face is not None:
        (tmp_path / "face_flops.tcl").write_text(face)
    return tmp_path


PRE = "foreach i $ot_hb { $i setDoNotTouch 1 }\nif {[string match *u_hdly_* [$i getName]]} {}\n"


def test_gen_lint_check(tmp_path):
    assert GL.hdly_nets_dnt(_kit(tmp_path / "a", None, None) if (tmp_path / "a").mkdir() is None else None) == ([], False)
    (tmp_path / "b").mkdir()
    assert GL.hdly_nets_dnt(_kit(tmp_path / "b", "set x 1\n", "")) == ([], False)          # no pads: NA
    (tmp_path / "c").mkdir()
    ok = GL.hdly_nets_dnt(_kit(tmp_path / "c", PRE, SRC))
    assert ok == ([], True)
    (tmp_path / "d").mkdir()
    errs, on = GL.hdly_nets_dnt(_kit(tmp_path / "d", PRE, "# old hook\n"))
    assert on and "does not call ff_hdly_nets_dnt" in errs[0]
    (tmp_path / "e").mkdir()
    errs, on = GL.hdly_nets_dnt(_kit(tmp_path / "e", PRE, SRC, "export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl\nexport OT_HDLY_NETS_DNT = 0\n"))
    assert on and "OT_HDLY_NETS_DNT = 0" in errs[0]
    (tmp_path / "f").mkdir()
    errs, on = GL.hdly_nets_dnt(_kit(tmp_path / "f", PRE, SRC, "export DESIGN_NAME = t\n"))
    assert on and "no PRE_GLOBAL_PLACE_TCL" in errs[0]


def test_lint_reports_the_check(tmp_path):
    k = _kit(tmp_path, PRE, "# old hook\n", "export DESIGN_NAME = t\nexport PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl\nexport VERILOG_FILES = /work/t.v\n")
    (k / "t.v").write_text("module t; endmodule\n")
    r = GL.lint(k, yosys=False)
    assert r["checks"]["hdly_nets_dnt"]["verdict"] == "FAIL" and r["verdict"] == "FAIL"
