"""CLAND-BIN 11-15 (FABLE-GENBUG G2): capture register behind a landing ring is sited beside its ring flop."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCL = (HERE / "landing_placement.tcl").read_text()
pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def _procs(*names):
    out = ""
    for n in names:
        m = re.search(r"^proc %s \{[^\n]*\n(?:.*?\n)??\}\n" % n, TCL, re.S | re.M)
        assert m, n
        out += m.group(0)
    return out


def _run(body):
    return subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split("\n")


def test_row_x_nearest_free_gap():
    # row 0..1000 (site 10), occupied [100,300) and [350,600); cell 40 wide wants centre 330 (inside the hole 300..350)
    body = _procs("cland_bin_row_x") + "puts [cland_bin_row_x {{100 300} {350 600}} 330 40 0 1000 0 10]\n"
    assert _run(body)[0] == "310 0.0"  # the 50-wide hole takes the 40-wide cell centred on the target


def test_row_x_hole_too_small_goes_to_next_segment():
    body = _procs("cland_bin_row_x") + "puts [cland_bin_row_x {{100 300} {330 600}} 320 40 0 1000 0 10]\n"
    out = _run(body)[0].split()
    assert out[0] == "60"  # the 30-wide hole is too small; x 60 (centre 80, 240 away) beats x 600 (centre 620, 300 away)


def test_row_x_full_row_has_no_site():
    body = _procs("cland_bin_row_x") + "puts [llength [cland_bin_row_x {{0 1000}} 500 40 0 1000 0 10]]\n"
    assert _run(body)[0] == "0"


def test_row_x_stays_inside_core_and_on_the_site_grid():
    body = _procs("cland_bin_row_x") + "puts [cland_bin_row_x {} 3 40 5 100 5 7]\n"
    x = int(_run(body)[0].split()[0])
    assert x >= 5 and (x - 5) % 7 == 0 and x + 40 <= 100


def test_site_search_prefers_own_row_then_neighbour(tmp_path):
    # a fake odb inst: proc named f answering getMaster/getWidth/getHeight via a dispatcher
    body = ("proc cland_family_w {m} { return 54 }\n"
            "proc f {cmd args} { switch $cmd { getMaster {return M} } }\n"
            "proc M {cmd args} { switch $cmd { getWidth {return 54} getHeight {return 270} } }\n"
            "set ff_x0 0; set ff_y0 0; set ff_x1 10000; set ff_y1 2700; set ff_rh 270; set ff_sw 54\n"
            "set ff_orient {}; for {set y 0} {$y < 2700} {incr y 270} { dict set ff_orient $y R0 }\n"
            "set cland_occ {}\n"
            "dict set cland_occ 1 {{0 10000}}\n"      # the ring's own row (y 270) is full
            + _procs("cland_bin_row_x", "cland_bin_site") +
            "puts [cland_bin_site f 1000 300 100000]\n")
    out = _run(body)[0].split()
    assert int(out[1]) in (0, 540)           # nearest rows above/below the full one
    assert abs(int(out[0]) + 27 - 1000) <= 54


def test_site_search_respects_radius():
    body = ("proc cland_family_w {m} { return 54 }\n"
            "proc f {cmd args} { switch $cmd { getMaster {return M} } }\n"
            "proc M {cmd args} { switch $cmd { getWidth {return 54} getHeight {return 270} } }\n"
            "set ff_x0 0; set ff_y0 0; set ff_x1 10000; set ff_y1 2700; set ff_rh 270; set ff_sw 54\n"
            "set ff_orient {}; for {set y 0} {$y < 2700} {incr y 270} { dict set ff_orient $y R0 }\n"
            "set cland_occ {}\nfor {set r 0} {$r < 10} {incr r} { dict set cland_occ $r {{0 10000}} }\n"
            + _procs("cland_bin_row_x", "cland_bin_site") +
            "puts [llength [cland_bin_site f 1000 300 100000]]\n")
    assert _run(body)[0] == "0"


def test_block_runs_after_every_ring_and_releases_with_them():
    i_ring = TCL.index("foreach spec $cland_groups {\n lassign $spec prefix rect tag\n# BEGIN NATIVE_ROLE_BANKS")
    i_bin = TCL.index("set cland_bin_moved [cland_bin_place]")
    i_close = TCL.index("close $cland_fh\nputs \"OT_CLAND placed")
    assert i_ring < i_bin < i_close
    assert 'puts $cland_fh "$sn\\tcland:bin:$bus' in TCL          # face_flops_release.tcl frees every name in this file
    assert "OT_CLAND_BIN bus $bus placed $nplaced of $nfound" in TCL
    assert "$nplaced < 0.95*$nfound" in TCL
    assert "OT_CLAND_BIN_WARN" in TCL


def test_opt_in_default_is_off():
    assert "[info exists ::env(OT_CLAND_BIN)] ? $::env(OT_CLAND_BIN) : 0" in TCL
    assert "if {$mode ni {1 eq}}" in TCL


def test_equal_hop_point_is_on_the_ring_to_anchor_line():
    body = _procs("cland_bin_point") + "puts [cland_bin_point 0 0 640000 100000 0.5]\nputs [cland_bin_point 10 10 110 410 0.25]\n"
    out = _run(body)
    assert out[0] == "320000.0 50000.0" and out[1] == "35.0 110.0"


def test_anchor_walk_is_by_master_and_bounded():
    body = _procs("cland_bin_anchor")
    assert "$rank <= 3" in body and "[[$i getMaster] isBlock]" in body and "FIRM LOCKED" in body
    assert "u_bin" not in body and "u_st" not in body
    assert TCL.index("# CLAND-BIN BEGIN") < TCL.index("proc cland_bin_row_x") < TCL.index("# CLAND-BIN END")


def test_sinks_are_matched_by_master_not_name():
    body = _procs("cland_bin_sinks")
    assert "regexp {^(BUF|INV|HB)} $mn" in body
    assert "DFF|DHL|DLL|SDF" in body and "u_bin" not in body
    assert '[[$it getMTerm] getName] eq "D"' in body


def test_moved_capture_registers_get_their_reset_re_pointed():
    assert "foreach n $cland_bin_moved { lappend ff_landed_moved $n }" in TCL
    assert TCL.index("foreach n $cland_bin_moved") < TCL.index("source /work/reset_taps.tcl")


def test_plan_site_lookup_prefers_the_bit_key_then_the_bus_key():
    body = _procs("cland_bin_site_of") + \
        "set s [dict create bc_i02 {1 2} {bc_i02[7]} {3 4}]\n" \
        "puts [cland_bin_site_of $s bc_i02 7]\nputs [cland_bin_site_of $s bc_i02 8]\nputs [cland_bin_site_of $s bc_i02 {}]\nputs [llength [cland_bin_site_of $s nb_i12 7]]\n"
    assert _run(body)[:4] == ["3 4", "1 2", "1 2", "0"]


def test_plan_site_form_places_ust_and_takes_the_bit_from_the_capture_name():
    body = _procs("cland_bin_loads")
    assert "[[$it getMTerm] getName] eq \"D\"" in body and "u_st" not in body
    m = re.search(r'regexp \{(q[^}]*)\} \$sn -> bit', TCL)
    assert m
    out = _run('puts [regexp {%s} {u_bound.u_bin_bc_i02/q\\[42\\]$_DFF_P_} -> b]; puts $b\n' % m.group(1))
    assert out[:2] == ["1", "42"]
    assert "cland:bin-ust:" in TCL and "/work/cland_bin_sites.tcl" in TCL


def test_capture_register_takes_its_plan_site_when_the_sidecar_has_one():
    assert 'cland_bin_site_of $sites "${bus}:bin" $bit' in TCL and "incr nbplan" in TCL
    assert TCL.index("set bsite {}") < TCL.index("incr nbplan") < TCL.index("lassign [cland_bin_point")


def test_u_bin_only_plan_entry_is_taken_without_a_u_st_site():
    assert 'set bsite [cland_bin_site_of $sites "${bus}:bin" $bit]' in TCL
    assert "u_bin-only entry" in TCL
    assert TCL.index("set bsite [cland_bin_site_of") < TCL.index("u_bin-only entry") < TCL.index("incr nbplan")
