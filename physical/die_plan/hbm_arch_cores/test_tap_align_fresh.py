from pathlib import Path
import subprocess

SRC = Path(__file__).with_name("core_tap_align.tcl").read_text()


def _proc(name):
    i = SRC.index(f"proc {name} ")
    return SRC[i:SRC.index("\n}\n", i) + 3]


def _check(cf, ref, tol=1.0, mode="fail"):
    p = subprocess.run(["tclsh"], input=_proc("ta_fresh_check") + f"if {{[catch {{puts [ta_fresh_check t p {cf} {{{ref}}} {tol} {mode}]}} e]}} {{puts \"ERR $e\"; exit 3}}\n",
                       text=True, capture_output=True)
    return p.returncode, p.stdout + p.stderr


def test_measure_forces_a_full_search_before_reading():
    body = _proc("ta_measure")
    assert body.index("sta::find_timing 1") < body.index("ot_cf_wire")


def test_every_tap_cross_checks_one_sink():
    body = _proc("ta_measure")
    assert "set xc 0" in body and "ta_fresh_check $n $p $a" in body and "set xc 1" in body


def test_agreeing_arrival_passes():
    rc, out = _check(822.598, 822.5985)
    assert rc == 0 and out.strip() == "1"


def test_stale_arrival_fails_loudly():
    rc, out = _check(617.0, 822.6)  # v512b ot_dtap_700011: stale mean vs fresh arrival
    assert rc != 0 and "OT_DTAP_ALIGN STALE t" in out


def test_missing_direct_arrival_fails():
    for ref in ("", "INF"):
        rc, out = _check(617.0, ref)
        assert rc != 0 and "cross-check impossible" in out


def test_direct_reference_takes_the_active_edge_off():
    # live v512b 4_cts: a negative-edge sink read 707.59 (edge-relative) vs 1124.09 absolute without this
    body = _proc("ta_measure")
    assert "lappend wf [sta::time_sta_ui $t]" in body
    assert 'set ref [expr {$ref - [lindex $wf [expr {$tr eq "fall" ? 1 : 0}]]}]' in body


def test_default_mode_warns_and_continues():
    rc, out = _check(617.0, 822.6, mode="warn")
    assert rc == 0 and "WARN OT_DTAP_ALIGN STALE t" in out and out.strip().endswith("0")
    assert 'set ta_xcheck_mode [expr {[info exists ::env(OT_DTAP_XCHECK_MODE)] ? $::env(OT_DTAP_XCHECK_MODE) : "warn"}]' in SRC


def test_forced_search_is_unconditional():
    body = _proc("ta_measure")
    line = next(l for l in body.splitlines() if "sta::find_timing 1" in l)
    assert line.strip() == "sta::find_timing 1"
