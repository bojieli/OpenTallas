"""FLOW-CLASS-25 11-06 (COORD 18:0x (3c)): OT_FINAL_FF_HOLD in a kit's config.mk gates the final FF hold pass in the
generated core_grt_post.tcl (default unchanged: on)."""
import shutil
import subprocess

import pytest

import gen_core_kit_hbm as G

BASE = ("if {[info exists ::env(OT_VCLK_CORNER)] && $::env(OT_VCLK_CORNER) eq \"ff\"} { ot_vclk_bind tt }\n"
        "uplevel #0 [list source /work/pg_connect.tcl]\not_pg_connect_all grt_post\not_pg_require_bound grt_post\n")


def run(env):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    post = G.final_ff_hold_post(BASE)
    tcl = ("set ::calls {}\n" + ("unset -nocomplain ::env(OT_FINAL_FF_HOLD)\n" if env is None
                                  else "set ::env(OT_FINAL_FF_HOLD) %s\n" % env) +
           "proc source {f} { lappend ::calls [list source [file tail $f]] }\n"
           "proc ot_final_ff_hold {} { lappend ::calls final_ff_hold }\n"
           "proc ot_pg_connect_all {s} { lappend ::calls pg }\nproc ot_pg_require_bound {s} {}\n"
           + post + "puts \"CALLS $::calls\"\n")
    return subprocess.run(["tclsh"], input=tcl, text=True, capture_output=True, check=True).stdout


def test_default_and_one_run_the_pass_before_pg():
    for env in (None, "1"):
        out = run(env)
        assert "CALLS {source final_ff_hold.tcl} final_ff_hold {source pg_connect.tcl} pg" in out, out


def test_zero_skips_the_pass():
    out = run("0")
    assert "OT_FINAL_FF_HOLD skipped (OT_FINAL_FF_HOLD=0)" in out
    assert "final_ff_hold" not in out.split("CALLS", 1)[1] and "{source pg_connect.tcl} pg" in out


def test_anchor_required():
    with pytest.raises(SystemExit):
        G.final_ff_hold_post("puts no_pg\n")


def test_generator_uses_the_gate():
    src = (G.Path(G.__file__)).read_text()
    assert "final_ff_hold_post(post.read_text())" in src
    assert "\\not_final_ff_hold\\n\"" not in src     # no ungated call left
