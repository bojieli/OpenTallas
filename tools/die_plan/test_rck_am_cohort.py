"""RCK AM cohort: actual hierarchy, >64-buffer roots and a gated negative."""
import subprocess
import tempfile
from pathlib import Path

HOOK = Path(__file__).with_name("rck_am_cohort.tcl")


def _run(enabled=True, gated=False, missing=False):
    lines = [
        "set la_ck {};set la_groot_c {};set la_moved 0;set calls 0",
        "set drivers {};set pin_net {}",
        "proc la_drv {net} {if {[dict exists $::drivers $net]} {return [dict get $::drivers $net]};return {}}",
        "proc la_is_bufinv {inst} {return [string match buf* $inst]}",
        "proc dbnet {name method} {return $name}",
        "proc dbmaster {method} {return BUFx24_ASAP7_75t_R}",
        "interp alias {} mbuf {} dbmaster",
        "proc dbinst {name method} {switch $method {getName {return $name} getMaster {return mbuf} getITerms {return [list ip_$name]}}}",
        "proc dbpin {name method} {switch $method {getNet {return [dict get $::pin_net $name]} isInputSignal {return 1}}}",
        "proc la_try {members} {if {[llength $members]!=7} {error {wrong group shape}};incr ::calls;incr ::la_moved 3;return moved}",
    ]
    for i in range(71):
        lines.append(f"interp alias {{}} net{i} {{}} dbnet net{i}")
        if i < 70:
            lines += [f"interp alias {{}} buf{i} {{}} dbinst buf{i}",
                      f"interp alias {{}} ip_buf{i} {{}} dbpin ip_buf{i}",
                      f"dict set drivers net{i} buf{i}", f"dict set pin_net ip_buf{i} net{i+1}"]
    lines += ["interp alias {} net_gate {} dbnet net_gate",
              "interp alias {} gate {} dbinst gate", "dict set drivers net_gate gate"]
    names = [f"u_bound.u_core.u_rxf_q\\[{i}\\]$_DFF_N_" for i in range(532, 544)]
    names += [f"u_bound.u_core.u_dec.u_face_am3.parts\\[{i}\\]$_DFF_P_" for i in range(9)]
    if missing:
        names.pop(0)
    for i, name in enumerate(names):
        net = "net_gate" if gated and "parts\\[0" in name else "net0"
        lines += [f"interp alias {{}} p{i} {{}} dbpin p{i}",
                  f"dict set pin_net p{i} {net}", f"dict set la_ck {{{name}}} p{i}"]
    if enabled:
        lines.append("set ::env(OT_S81_RCK_AM_COHORT) 1")
    lines += [f"source {{{HOOK}}}", "puts \"CALLS=$calls\""]
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "test.tcl"
        p.write_text("\n".join(lines) + "\n")
        return subprocess.run(["tclsh", str(p)], text=True, capture_output=True)


def test_default_off_changes_no_clock():
    r = _run(enabled=False)
    assert r.returncode == 0 and "CALLS=0" in r.stdout


def test_actual_header_am_shape_and_deep_buffer_root():
    r = _run()
    assert r.returncode == 0, r.stderr
    assert "CALLS=3" in r.stdout and "actual_root port:net70:0" in r.stdout


def test_different_actual_gating_root_rejected():
    r = _run(gated=True)
    assert r.returncode != 0 and "different actual clock/gating roots" in r.stderr


def test_missing_header_rejected_before_clock_change():
    r = _run(missing=True)
    assert r.returncode != 0 and "11/12" in r.stderr
