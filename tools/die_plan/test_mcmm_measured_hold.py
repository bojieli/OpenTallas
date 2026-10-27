import subprocess
from pathlib import Path
HERE=Path(__file__).parent

def test_measured_binding_only_changes_ff_mode(tmp_path):
    """Different FF/TT constraints stay isolated when BC reference is rebound."""
    helper=HERE/"vclk_measured_hold.tcl"
    script=f"""
source {helper}
rename ot_vmh_reference original_reference
proc ot_vmh_reference {{}} {{return {{rebind 202.5 40}}}}
rename ot_vmh_pinreg_mean original_mean
proc ot_vmh_pinreg_mean {{}} {{return {{195 10 0 1}}}}
set mode ff
array set latency {{ss 250 ff 202.5}}
proc all_clocks {{}} {{return {{real virtual}}}}
proc get_property {{o p}} {{if {{$p eq "sources"}} {{if {{$o eq "real"}} {{return CK}}; return {{}}}}}}
proc estimate_parasitics {{args}} {{}}
proc get_full_name {{o}} {{return $o}}
proc set_clock_latency {{a value clock}} {{set ::latency($::mode) $value}}
ot_vclk_measured_bind
if {{$latency(ss) != 250 || $latency(ff) != 195}} {{error "mode corruption"}}
rename ot_vmh_pinreg_mean original_mean2
proc ot_vmh_pinreg_mean {{}} {{return {{100 10 0 1}}}}
if {{![catch {{ot_vclk_measured_bind}} err]}} {{error "out-of-band accepted"}}
if {{$latency(ff) != 195}} {{error "out-of-band mutated constraints"}}
puts PASS
"""
    r=subprocess.run(["tclsh"],input=script,text=True,capture_output=True)
    assert r.returncode==0 and "PASS" in r.stdout and not r.stderr, r

def test_mm_binds_before_repair_in_bc_shim():
    s=(HERE.parent/"orfs_hold_mm.tcl").read_text()
    body=s[s.index("proc ot_mm_sync {}"):s.index("proc ot_mm_unsync {}")]
    assert body.index("ot_mm_scene_shim 1") < body.index("ot_vclk_measured_bind") < body.index("ot_mm_scene_shim 0")
    assert body.index("set_mode ff") < body.index("ot_vclk_measured_bind") < body.index("set_mode ss",body.index("ot_vclk_measured_bind"))

