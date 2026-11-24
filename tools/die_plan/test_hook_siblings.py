"""HOOK-SIBLINGS-1124: kit gen stages every sibling a staged hook sources (tap_landing_seam.tcl), kit_preflight refuses a kit that lacks one."""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys as GP  # noqa: E402
import kit_preflight as KP  # noqa: E402


def test_hook_closure_stages_tap_landing_seam_and_every_sibling():
    names = GP.hook_closure(("clock_taps.tcl",))
    assert "tap_landing_seam.tcl" in names
    src = (HERE / "gen_phys.py").read_text()
    i = src.index("for f in hook_closure((")
    staged = GP.hook_closure(eval(src[i + len("for f in hook_closure("):src.index(")):", i) + 1]))
    for n in staged:                                           # every sibling an unguarded staged hook sources is staged too
        f = HERE / n
        if f.suffix == ".tcl" and f.is_file():
            for m in GP._HOOK_SIBLING_RE.findall(f.read_text(errors="replace")):
                assert m in staged or not (HERE / m).is_file(), (n, m)


def test_preflight_refuses_a_missing_sourced_hook(tmp_path):
    (tmp_path / "clock_taps.tcl").write_text(
        "if {[info exists ::env(OT_TAP_LANDING_SEAM)] && $::env(OT_TAP_LANDING_SEAM) eq \"1\"} {\n"
        " source [file join [file dirname [info script]] tap_landing_seam.tcl]\n}\n"
        "source /work/reset_taps.tcl\n"
        "foreach cf [list /work/clock_family.tcl] {\n  if {[file exists $cf]} { source $cf; break }\n}\n"
        "if {[file exists /work/opt.tcl]} {\n  source /work/opt.tcl\n}\n")
    (tmp_path / "config.mk").write_text("export OT_TAP_LANDING_SEAM = 1\n")
    err = KP.hook_sources(tmp_path)
    assert len(err) == 2 and any("tap_landing_seam.tcl" in e for e in err) and any("reset_taps.tcl" in e for e in err)
    (tmp_path / "reset_taps.tcl").write_text("")
    (tmp_path / "config.mk").write_text("export OT_TAP_LANDING_SEAM = 0\n")      # flag off: never runs here -> advisory only
    adv = []
    assert KP.hook_sources(tmp_path, adv) == [] and len(adv) == 1
    (tmp_path / "config.mk").write_text("export OT_TAP_LANDING_SEAM = 1\n")
    (tmp_path / "tap_landing_seam.tcl").write_text("")
    assert KP.hook_sources(tmp_path) == []
