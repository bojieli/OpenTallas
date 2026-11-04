import os
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
if {{[info exists ::env(OT_POSTCTS_BAND_GATE)] && $::env(OT_POSTCTS_BAND_GATE) eq "1"}} {{
  if {{![catch {{ot_vclk_measured_bind}} err]}} {{error "out-of-band accepted under OT_POSTCTS_BAND_GATE=1"}}
  if {{$latency(ff) != 195}} {{error "out-of-band mutated constraints"}}
}} else {{
  ot_vclk_measured_bind
  if {{$latency(ss) != 250 || $latency(ff) != 100}} {{error "advisory band: ff not bound to measured mean or ss touched"}}
}}
puts PASS
"""
    # KW-FIX-4/BAND 11-03 (OWNER 19:12): an out-of-band FF mean is ADVISORY by default (binds, no stop);
    # OT_POSTCTS_BAND_GATE=1 keeps the old fail-closed stop.  Both modes are checked; ss stays isolated in both.
    for gate in ("", "1"):
        env = dict(os.environ, OT_POSTCTS_BAND_GATE=gate)
        r=subprocess.run(["tclsh"],input=script,text=True,capture_output=True,env=env)
        assert r.returncode==0 and "PASS" in r.stdout, (gate, r)

def test_mm_binds_before_repair_in_bc_shim():
    s=(HERE.parent/"orfs_hold_mm.tcl").read_text()
    body=s[s.index("proc ot_mm_sync {}"):s.index("proc ot_mm_unsync {}")]
    assert body.index("ot_mm_scene_shim 1") < body.index("ot_vclk_measured_bind") < body.index("ot_mm_scene_shim 0")
    assert body.index("set_mode ff") < body.index("ot_vclk_measured_bind") < body.index("set_mode ss",body.index("ot_vclk_measured_bind"))


def test_measured_mm_preflight_and_incomplete_controls(tmp_path):
    import kit_modes
    import sdc_lint
    from test_kit_modes import kit
    kd=kit(tmp_path)
    assert kit_modes.main(["stage", str(kd), "--measured-hold"]) == 0
    assert not (kd/"grt_post.tcl").exists()
    assert sdc_lint.measured_frame_errors(kd) == []
    mm=kd/"orfs_hold_mm.tcl"
    text=mm.read_text()
    mm.write_text(text.replace("ot_vclk_measured_bind", "missing_bind"))
    assert "incomplete" in sdc_lint.measured_frame_errors(kd)[0]
    mm.write_text(text)
    (kd/"config.mk").write_text((kd/"config.mk").read_text().replace("override export OT_HOLD_MM = 1", "override export OT_HOLD_MM = 0"))
    assert "incomplete" in sdc_lint.measured_frame_errors(kd)[0]

