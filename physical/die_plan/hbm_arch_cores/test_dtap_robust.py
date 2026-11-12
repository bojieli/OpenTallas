import subprocess
from pathlib import Path

SRC = Path(__file__).with_name("core_tap_align.tcl").read_text()
NAMES = ("ta_root_of", "ta_main_root", "ta_robust_target", "ta_outliers", "ta_predict")


def _proc(name):
    i = SRC.index(f"proc {name} ")
    return SRC[i:SRC.index("\n}\n", i) + 3]


def _run(body):
    tcl = "\n".join(_proc(n) for n in NAMES) + "\n" + body
    p = subprocess.run(["tclsh"], input=tcl, text=True, capture_output=True)
    assert p.returncode == 0, p.stderr
    return p.stdout.strip()


# v32e0 attempt_2 r0 (main root 7 = 40 taps 581..727 plus ot_dtap_700028 at 937; macro roots 1 sink; side roots earlier)
main = " ".join("ot_dtap_%d {%d 0 0 60}" % (700100 + i, 581 + round(i * 146 / 38)) for i in range(39))
V32 = main + " ot_dtap_700028 {937 0 0 18} ot_dtap_200000 {90 0 0 1} ot_dtap_500000 {327 0 0 40} ot_dtap_08 {320 0 0 40}"


def test_default_target_is_the_global_max_and_robust_is_opt_in():
    assert "OT_DTAP_ALIGN_ROBUST" in SRC
    assert "set ta_rob [expr {[info exists ::env(OT_DTAP_ALIGN_ROBUST)] && $::env(OT_DTAP_ALIGN_ROBUST)}]" in SRC
    # the plain target line is untouched and runs before the opt-in block
    assert SRC.index("set ta_tgt 0.0; dict for") < SRC.index("set ta_rob ")


def test_octal_looking_ids_do_not_crash():
    assert _run("puts [ta_root_of ot_dtap_08]; puts [ta_root_of ot_dtap_700028]; puts [ta_root_of other]").split() == ["0", "7", "-1"]


def test_robust_target_ignores_the_single_late_tap_and_other_roots():
    out = _run(f"set m [dict create {V32}]; puts [ta_robust_target $m [dict create] 90 2]")
    assert 700 <= float(out) <= 730  # p90 of the 40 main-root taps (>= 2 sinks), nearest rank = 36th, far below 937
    out = _run(f"set m [dict create {V32}]; puts [ta_main_root $m]")
    assert out == "7"


def test_outlier_is_found_and_costs_no_cells():
    body = f"set m [dict create {V32}]; set t [ta_robust_target $m [dict create] 90 2]; puts [ta_outliers $m [dict create] $t 40]"
    assert _run(body) == "ot_dtap_700028"
    body = f"set m [dict create {V32}]; set l [dict create]; puts [dict get [ta_predict $m $l 937 15.3 {{}}] 7]; puts [dict get [ta_predict $m $l 700 15.3 ot_dtap_700028] 7]"
    a, b = _run(body).splitlines()
    assert int(a.split()[1]) > int(b.split()[1])


def test_lead_taps_do_not_set_the_target():
    body = f"set m [dict create {V32}]; set l [dict create ot_dtap_700000 10.0]; puts [ta_robust_target $m $l 90 2]"
    assert 700 <= float(_run(body)) <= 730


def test_only_one_sink_taps_fall_back_to_all():
    assert float(_run("set m [dict create ot_dtap_100000 {90 0 0 1}]; puts [ta_robust_target $m [dict create] 90 2]")) == 90.0


def test_rehome_keeps_only_a_real_improvement_and_restores():
    i = SRC.index("OT_DTAP_ALIGN_OUTLIER")
    assert "OT_DTAP_REHOME_MIN_PS" in SRC and "put back, kept-unpadded" in SRC and "$isoA disconnect; $isoA connect $oldnet" in SRC
    assert i > 0


def test_chains_with_lead_and_other_hooks():
    # ALIGN_LEAD reads ta_lead before the robust block; the final hook stays OT_DTAP_NEXT
    assert SRC.index("set ta_lead [dict create]") < SRC.index("set ta_rob ")
    assert SRC.rstrip().splitlines()[-1].startswith("if {$ta_next ne")
