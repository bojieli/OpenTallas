"""R369 exact-cohort contract, using a minimal actual OpenDB macro fixture."""
import os
import json
from pathlib import Path
import shutil
import subprocess

import pytest

import s81_svc_live_sites as s


LEF = '''VERSION 5.8 ;
BUSBITCHARS "[]" ; DIVIDERCHAR "/" ;
UNITS DATABASE MICRONS 1000 ; END UNITS
MANUFACTURINGGRID 0.001 ;
LAYER M1 TYPE ROUTING ; DIRECTION HORIZONTAL ; PITCH 1 ; WIDTH 0.1 ; END M1
SITE unit CLASS CORE ; SIZE 1 BY 1 ; SYMMETRY X Y ; END unit
MACRO ot_sram_1r1w_32x128_m1_r0c0
 CLASS BLOCK ; ORIGIN 0 0 ; SIZE 2 BY 2 ; SYMMETRY X Y ;
 PIN D DIRECTION INPUT ; USE SIGNAL ; PORT LAYER M1 ; RECT 0.1 0.1 0.2 0.2 ; END END D
END ot_sram_1r1w_32x128_m1_r0c0
END LIBRARY
'''


def _script(t):
    names = ["other_live_a", *s.expected_names(t), "other_live_b"]
    return "# Original declared placement, including all eight slots.\n" + "".join(
        "place_macro -macro_name {%s} -location {%d 20} -orientation R0 -exact\n"
        % (n.replace("[", "\\[").replace("]", "\\]"), 10 + i * 5)
        for i, n in enumerate(names))


def _run(tmp_path, t, present, unrelated=False):
    exe = os.environ.get("OPENROAD_BIN")
    docker = shutil.which("docker")
    if not exe and (not docker or subprocess.run(
            [docker, "image", "inspect", "openroad/orfs:asap7lock"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode):
        pytest.skip("qualified OpenROAD image unavailable (or set OPENROAD_BIN)")
    (tmp_path / "m.lef").write_text(LEF)
    (tmp_path / "t.v").write_text("module t(input clk); endmodule\n")
    original = _script(t)
    if unrelated:
        original += "place_macro -macro_name {UNRELATED_MISSING} -location {90 20} -orientation R0 -exact\n"
    (tmp_path / "placement.tcl").write_text(s.wrap(t, original, enabled=True))
    names = ["other_live_a", *s.expected_names(t)[:present], "other_live_b"]
    create = "\n".join(
        "set i [odb::dbInst_create $b $m {%s}]; $i setLocation 1000 1000"
        % n.replace("[", "\\[").replace("]", "\\]")
        for n in names)
    expected_error = "SVC_R369 mixed bank presence" if present not in (0, 8) else ("MPL-0020" if unrelated else "")
    script = '''read_lef {%s/m.lef}
read_verilog {%s/t.v}
link_design t
initialize_floorplan -die_area {0 0 200 200} -core_area {0 0 200 200} -site unit
set b [ord::get_db_block]
set m [[ord::get_db] findMaster ot_sram_1r1w_32x128_m1_r0c0]
%s
set before {}
foreach i [$b getInsts] {lappend before [list [$i getName] [[$i getMaster] getName]]}
set poses {}; foreach i [$b getInsts] {dict set poses [$i getName] [list [$i getLocation] [$i getPlacementStatus]]}
set rc [catch {source {%s/placement.tcl}} message]
puts "RESULT $rc $message"
set after {}
foreach i [$b getInsts] {lappend after [list [$i getName] [[$i getMaster] getName]]}
if {[lsort $before] ne [lsort $after]} {error "cell/master inventory changed"}
if {[llength [info commands ::place_macro]] != 1 || [llength [info commands ::s81_svc_r369::original_place_macro]]} {error "native command not restored"}
%s
puts FIXTURE_CHECK_PASS
''' % (tmp_path, tmp_path, create, tmp_path,
       ('if {!$rc || [string first {%s} $message] < 0} {error "wrong or missing expected failure"}\n' % expected_error)
       if expected_error else 'if {$rc} {error $message}\n')
    if present not in (0, 8):
        script += '''foreach i [$b getInsts] {
 if {[dict get $poses [$i getName]] ne [list [$i getLocation] [$i getPlacementStatus]]} {error "mixed cohort mutated placement"}
}
puts MIXED_UNTOUCHED
'''
    if unrelated:
        script += 'if {[string first UNRELATED_MISSING $message] < 0} {error "unrelated error hidden"}\n'
    (tmp_path / "run.tcl").write_text(script)
    args = ["-no_init", "-exit", str(tmp_path / "run.tcl")]
    cmd = ([exe, *args] if exe else [
        docker, "run", "--rm", "--network=none", "--user", f"{os.getuid()}:{os.getgid()}",
        "-v", f"{tmp_path}:{tmp_path}:ro", "openroad/orfs:asap7lock", "bash", "-lc",
        'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; exec openroad "$@"', "bash", *args])
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert "FIXTURE_CHECK_PASS" in r.stdout, r.stdout + r.stderr
    if not expected_error:
        assert r.returncode == 0, r.stdout + r.stderr
        assert f"skipped={8 if present == 0 else 0}" in r.stdout
    if present not in (0, 8):
        assert "MIXED_UNTOUCHED" in r.stdout
    return r.stdout


def test_default_and_unrelated_types_are_byte_identical():
    text = _script("svc_hi_dsdv_svc_rs__t3")
    assert s.wrap("svc_hi_dsdv_svc_rs__t3", text) == text
    assert s.wrap("unrelated_type", text, enabled=True) == text


def test_incomplete_declaration_refuses():
    text = _script("svc_hi_dsdv_svc_rs__t3")
    first = s.expected_names("svc_hi_dsdv_svc_rs__t3")[0].replace("[", "\\[").replace("]", "\\]")
    with pytest.raises(ValueError, match="exact eight"):
        s.wrap("svc_hi_dsdv_svc_rs__t3", text.replace(first, "other_macro"), enabled=True)


def test_actual_type_kit_gen_hook_preserves_default_config(tmp_path, monkeypatch):
    # Exercise the real partition-kit writer on its existing tiny plan, not a
    # whole-die GEN or synthesis. The macro deck is the only changed artifact.
    import gen_phys as G
    import schema as S
    here = Path(G.__file__).resolve().parent
    raw = json.loads((here / "examples/tiny_plan.json").read_text())
    tname = "svc_hi_dsdv_svc_rs__t3"
    raw["partition_types"][tname] = raw["partition_types"].pop("src")
    parts = raw["partitions"].values() if isinstance(raw["partitions"], dict) else raw["partitions"]
    for p in parts:
        if p["type"] == "src":
            p["type"] = tname
    master = "ot_sram_1r1w_32x128_m1_r0c0"
    (tmp_path / "m.lef").write_text(f"MACRO {master}\n SIZE 8.64 BY 8.64 ;\nEND {master}\n")
    (tmp_path / "m_tt.lib").write_text("library(m) {}\n")
    (tmp_path / "m_ff.lib").write_text("library(m_ff) {}\n")
    t = raw["partition_types"][tname]
    t.setdefault("contents", []).extend(dict(
        inst=n, physical_inst=n, module=master, physical_master=master, status="planned",
        lef="m.lef", lib="m_tt.lib", origin_um=[17.28+i*10.8, 25.92], outline_um=[8.64, 8.64])
        for i, n in enumerate(s.expected_names(tname)))
    monkeypatch.delenv("OT_S81_SVC_LIVE_SITES", raising=False)
    normal = G.write_type_kit(S.Plan(raw), tname, tmp_path / "normal", [], root=tmp_path)
    monkeypatch.setenv("OT_S81_SVC_LIVE_SITES", "1")
    guarded = G.write_type_kit(S.Plan(raw), tname, tmp_path / "guarded", [], root=tmp_path)
    old = (normal / "macro_place.tcl").read_text()
    assert "SVC_R369" not in old
    assert old in (guarded / "macro_place.tcl").read_text()
    assert (normal / "config.mk").read_bytes() == (guarded / "config.mk").read_bytes()
    assert (normal / "macro_skip_rtlmp.tcl").exists() == (guarded / "macro_skip_rtlmp.tcl").exists()


@pytest.mark.parametrize("t", tuple(s.PREFIX))
@pytest.mark.parametrize("present", (0, 8))
def test_real_odb_complete_cohort(tmp_path, t, present):
    _run(tmp_path, t, present)


def test_real_odb_mixed_presence_refuses_before_placement(tmp_path):
    _run(tmp_path, "svc_hi_dsdv_svc_rs__t3", 7)


def test_real_odb_unrelated_missing_still_native_mpl_failure(tmp_path):
    _run(tmp_path, "svc_hi_dsdv_svc_rs__t3", 0, unrelated=True)



def _pdn(t):
    names = ["other_live_a", *s.expected_names(t), "other_live_b"]
    pats = " ".join("{^%s$}" % n.replace(".", "\\.").replace("[", "\\\\\\[").replace("]", "\\\\\\]") for n in names)
    return ("# GENERATED pdn\nset_voltage_domain -name {CORE} -power {VDD} -ground {VSS}\n"
            "define_pdn_grid -macro -name {core_pg_M4} -instances {%s} -voltage_domains {CORE}\n" % pats)


def test_pdn_default_unrelated_and_no_grid_are_byte_identical():
    t = "svc_hi_dsdv_svc_rs__t3"
    text = _pdn(t)
    assert s.wrap_pdn(t, text) == text
    assert s.wrap_pdn("unrelated_type", text, enabled=True) == text
    plain = "define_pdn_grid -name {top} -voltage_domains {CORE} -pins {M7}\n"
    assert s.wrap_pdn(t, plain, enabled=True) == plain


def test_pdn_partial_declaration_refuses():
    t = "svc_hi_dsdv_svc_rs__t3"
    first = s.expected_names(t)[0].replace(".", "\\.").replace("[", "\\\\\\[").replace("]", "\\\\\\]")
    text = _pdn(t)
    assert first in text
    with pytest.raises(ValueError, match="exact eight"):
        s.wrap_pdn(t, text.replace(first, "other_macro"), enabled=True)


@pytest.mark.parametrize("present", (0, 8, 7))
def test_pdn_real_odb_cohort(tmp_path, present):
    exe = os.environ.get("OPENROAD_BIN")
    docker = shutil.which("docker")
    if not exe and (not docker or subprocess.run(
            [docker, "image", "inspect", "openroad/orfs:asap7lock"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode):
        pytest.skip("qualified OpenROAD image unavailable (or set OPENROAD_BIN)")
    t = "svc_hi_dsdv_svc_rs__t3"
    (tmp_path / "m.lef").write_text(LEF)
    (tmp_path / "t.v").write_text("module t(input clk); endmodule\n")
    (tmp_path / "pdn.tcl").write_text(s.wrap_pdn(t, _pdn(t), enabled=True))
    names = ["other_live_a", *s.expected_names(t)[:present], "other_live_b"]
    create = "\n".join("odb::dbInst_create $b $m {%s}" % n.replace("[", "\\[").replace("]", "\\]") for n in names)
    script = '''read_lef {%s/m.lef}
read_verilog {%s/t.v}
link_design t
set b [ord::get_db_block]
set m [[ord::get_db] findMaster ot_sram_1r1w_32x128_m1_r0c0]
%s
set ::got {}
rename ::define_pdn_grid ::real_dpg
proc ::define_pdn_grid {args} { set k [lsearch -exact $args -instances]; if {$k >= 0} {set ::got [lindex $args [expr {$k+1}]]} }
proc ::set_voltage_domain {args} {}
set rc [catch {source {%s/pdn.tcl}} message]
puts "RESULT $rc $message"
puts "GOT [llength $::got]"
if {[llength [info commands ::s81_svc_r369::original_define_pdn_grid]]} {error "native command not restored"}
puts FIXTURE_CHECK_PASS
''' % (tmp_path, tmp_path, create, tmp_path)
    (tmp_path / "run.tcl").write_text(script)
    args = ["-no_init", "-exit", str(tmp_path / "run.tcl")]
    cmd = ([exe, *args] if exe else [
        docker, "run", "--rm", "--network=none", "--user", f"{os.getuid()}:{os.getgid()}",
        "-v", f"{tmp_path}:{tmp_path}:ro", "openroad/orfs:asap7lock", "bash", "-lc",
        'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; exec openroad "$@"', "bash", *args])
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert "FIXTURE_CHECK_PASS" in r.stdout, r.stdout + r.stderr
    if present == 7:
        assert "RESULT 1" in r.stdout and "mixed bank presence" in r.stdout
    else:
        assert "RESULT 0" in r.stdout, r.stdout
        assert f"GOT {10 if present == 8 else 2}" in r.stdout, r.stdout
        assert f"pdn skipped={0 if present == 8 else 8}" in r.stdout
