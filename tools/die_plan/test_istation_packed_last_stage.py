"""GENBUG-1 (2026-11-15): the last register of a packed receiver delay (ot_dp_dly u_lpad_<bus>) is named after its
output port by Yosys (<inst>.q[b]), not <inst>.r[D-1][b].  The generated hook must place it on the last planned site,
and must fail when a pad that still has registers has none for a planned stage (silent partial coverage)."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_istations as K  # noqa: E402

TCLSH = shutil.which("tclsh")

MOCK = r'''
set ::placed {}
proc mk_inst {name master} {
  proc ::inst_$::nid {cmd args} [format {
    switch $cmd { getName { return {%s} } getMaster { return ::mast_%s } default { error "inst $cmd" } }
  } $name $::nid]
  proc ::mast_$::nid {cmd args} [format { if {$cmd eq "getName"} { return {%s} }; error "master $cmd" } $master]
  lappend ::insts ::inst_$::nid; incr ::nid
}
set ::nid 0; set ::insts {}
proc ff_blk_obj {cmd args} { if {$cmd eq "getInsts"} { return $::insts }; error "blk $cmd" }
set ff_blk ff_blk_obj; set ff_dbu 1000
proc ff_put_near {i x y} { lappend ::placed [list [$i getName] $x $y]; return [list $x $y] }
set ::env(RESULTS_DIR) $::tmpdir
'''


def _run(tmp_path, names, calls, env_cov=None):
    head = K.TCL_HEAD
    body = [f"set ::tmpdir {{{tmp_path}}}", MOCK]
    if env_cov:
        body.append(f"set ::env(OT_HOOK_COVERAGE) {env_cov}")
    for n, m in names:
        body.append(f"mk_inst {{{n}}} {m}")
    body.append(head)
    body += calls
    body.append('close $is_fh\nputs "OT_ISTATIONS placed $is_n flops FIRM (missing: [llength $is_miss] $is_miss)"\nis_coverage_gate')
    body.append('puts "PLACED $::placed"')
    f = tmp_path / "t.tcl"
    f.write_text("\n".join(body) + "\n")
    return subprocess.run([TCLSH, str(f)], capture_output=True, text=True)


def _pad(inst, depth, width, esc=True):
    """Yosys names of an ot_dp_dly: stages 0..D-2 are r[j][b], the last one is q[b]."""
    b = (lambda s: s.replace("[", "\\[").replace("]", "\\]")) if esc else (lambda s: s)
    out = []
    for j in range(depth - 1):
        out += [(f"u_bound.{inst}." + b(f"r[{j}][{k}]") + "$_DFF_P_", "DFFHQNx1_ASAP7_75t_R") for k in range(width)]
    out += [(f"u_bound.{inst}." + b(f"q[{k}]") + "$_DFF_P_", "DFFHQNx1_ASAP7_75t_R") for k in range(width)]
    return out


def _calls(inst, sites):
    d = len(sites); out = []
    anyg = "*" + inst + "[./]*"
    for j, (x, y) in enumerate(sites):
        pat = "*" + inst + f"[./]r\\[{j}\\]\\[*"
        alt = "*" + inst + "[./]q\\[*" if j == d - 1 else pat
        out.append(f"is_place_alt {{{pat}}} {{{alt}}} {{{anyg}}} {x} {y} ist:a")
    return out


def test_generator_emits_alias_for_last_stage_only():
    src = (HERE / "kit_istations.py").read_text()
    assert "is_place_alt {{{pattern}}} {{{alias}}} {{{anyg}}}" in src
    assert "if j == packed['depth'] - 1:" in src
    assert src.count("is_coverage_gate") >= 3  # proc + both emitters


def test_last_stage_named_q_is_placed_on_last_site(tmp_path):
    if not TCLSH:
        return
    r = _run(tmp_path, _pad("u_lpad_a", 4, 3) + [("u_bound.u_other.q\\[0\\]$_DFF_P_", "DFFHQNx1_ASAP7_75t_R")],
             _calls("u_lpad_a", [(10, 1), (20, 2), (30, 3), (40, 4)]))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OT_ISTATIONS placed 12 flops FIRM (missing: 0 )" in r.stdout
    assert "OT_HOOK_COVERAGE hook=istations touched=12 missing=0 packed_stage_unmatched=0" in r.stdout
    placed = re.search(r"PLACED (.*)", r.stdout).group(1)
    assert placed.count("40000 4000") == 3 and "u_other" not in placed  # q[b] of the pad only, on the last site


def test_depth_one_pad_is_q_only(tmp_path):
    if not TCLSH:
        return
    r = _run(tmp_path, _pad("u_lpad_a", 1, 2), _calls("u_lpad_a", [(5, 6)]))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "placed 2 flops FIRM (missing: 0 )" in r.stdout


def test_unescaped_names(tmp_path):
    if not TCLSH:
        return
    r = _run(tmp_path, _pad("u_lpad_a", 2, 2, esc=False), _calls("u_lpad_a", [(1, 1), (2, 2)]))
    assert r.returncode == 0 and "placed 4 flops FIRM (missing: 0 )" in r.stdout, r.stdout + r.stderr


def test_dead_pad_is_a_plain_miss(tmp_path):
    if not TCLSH:
        return
    r = _run(tmp_path, [("u_bound.u_x.q\\[0\\]$_DFF_P_", "DFFHQNx1_ASAP7_75t_R")], _calls("u_lpad_a", [(1, 1), (2, 2)]))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "missing=2 packed_stage_unmatched=0" in r.stdout


def test_live_pad_with_unmatched_stage_fails_closed(tmp_path):
    if not TCLSH:
        return
    names = [n for n in _pad("u_lpad_a", 3, 2) if "r\\[1\\]" not in n[0]]
    r = _run(tmp_path, names, _calls("u_lpad_a", [(1, 1), (2, 2), (3, 3)]))
    assert r.returncode != 0 and "OT_HOOK_COVERAGE istations: 1 planned packed stations matched no register" in r.stderr, r.stdout + r.stderr
    r = _run(tmp_path, names, _calls("u_lpad_a", [(1, 1), (2, 2), (3, 3)]), env_cov="warn")
    assert r.returncode == 0 and "OT_HOOK_COVERAGE WARN istations" in r.stdout, r.stdout + r.stderr
