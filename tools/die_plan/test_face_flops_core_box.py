"""FF-CORE-BOX (FABLE-FIX-S81-LEAF-R4 11-21; S81 leaf t44 / t39 vp block): ff_put_near never takes a station-grid cell that
touches a placed hard core (+ halo), so a register bank sited in or beside a core stays on one side of it instead of being
made FIRM on the core.  Real ff_put_near / ff_core_hit / ff_core_boxes_of from face_flops.tcl in tclsh.
    python3 -m pytest -q tools/die_plan/test_face_flops_core_box.py"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TCL = (Path(__file__).resolve().parent / "face_flops.tcl").read_text()
pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="no tclsh")


def _proc(name):
    i = TCL.index(f"proc {name} ")
    return TCL[i:TCL.index("\n}\n", i) + 3]


MOCK = r'''
proc flop {args} {
  switch -- [lindex $args 0] {
    getMaster { return master } getPlacementStatus { return PLACED } setPlacementStatus { return } setOrient { return }
    getName { return f } setLocation { set ::loc [lrange $args 1 2]; return }
  }
}
proc master {args} { switch -- [lindex $args 0] { getWidth { return 1080 } getHeight { return 270 } } }
proc ff_hits_explicit {args} { return 0 }
proc ff_pair_row_blocked {r} { return 0 }
set ff_gocc {}; set ff_x0 0; set ff_y0 0; set ff_x1 400000; set ff_y1 400000; set ff_rh 270; set ff_sw 54; set ff_cpitch 2160
set ff_orient {}; set ff_ns_stride 1; set ff_ns_inset 0; set ff_dbu 1000
'''


def _run(body):
    put = TCL[TCL.index("proc ff_put_near {f x y} {"):TCL.index("ot_ff_tick explicit_reserve_and_landed")]
    r = subprocess.run(["tclsh"], input=MOCK + _proc("ff_core_hit") + _proc("ff_core_boxes_of") + put + body, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stdout + r.stderr
    return r.stdout.split("\n")


def test_core_hit_and_halo():
    out = _run('set b [ff_core_boxes_of {{100000 100000 200000 200000}} 1080]\nputs $b\n'
               'puts "[ff_core_hit $b 98000 150000 1080 270] [ff_core_hit $b 97000 150000 1080 270] [ff_core_hit $b 150000 201000 1080 270] [ff_core_hit $b 150000 201080 1080 270] [ff_core_hit {} 150000 150000 1080 270]"\n')
    assert out[0] == "{98920 98920 201080 201080}" and out[1] == "1 0 1 0 0"


def test_bank_sited_inside_a_core_seats_outside_it_on_one_side():
    """1,025 flops asked at a point 3 um inside the west edge of a 100 x 100 um core: every flop lands clear of the core + halo"""
    out = _run('set ff_core_boxes [ff_core_boxes_of {{100000 100000 200000 200000}} 1080]\nset n 0; set bad 0; set east 0\n'
               'for {set i 0} {$i < 1025} {incr i} { set xy [ff_put_near flop 103000 150000]; if {$xy eq ""} continue; incr n\n'
               '  lassign $xy x y; if {[ff_core_hit $ff_core_boxes $x $y 1080 270]} {incr bad}; if {$x >= 200000} {incr east} }\n'
               'puts "$n $bad $east"\n')
    assert out[0] == "1025 0 0"


def test_no_boxes_is_the_old_behaviour():
    out = _run('set ff_core_boxes {}\nputs [ff_put_near flop 103000 150000]\nunset ff_core_boxes\nputs [ff_put_near flop 150000 150000]\n')
    assert out[0] == "101520 149850" and out[1] == "149040 149850"


def test_the_hook_builds_the_boxes_from_placed_blocks_and_both_searches_use_them():
    assert "if {![[$ff_cb_i getMaster] isBlock] || [$ff_cb_i getPlacementStatus] in {NONE UNPLACED}} continue" in TCL
    body = TCL[TCL.index("proc ff_put_near {f x y} {"):TCL.index("# interior pin registers")]
    assert body.count("[ff_core_hit $ff_core_boxes $cx $cy $w $ff_rh]") == 2          # NS face search and the spiral
    assert re.search(r"OT_FF_CORE_SKIP\)\] \|\| \$::env\(OT_FF_CORE_SKIP\) ne \"0\"", TCL)
