"""An early-tapped macro's planned IO frame must agree everywhere, in both corners."""
import json
import pytest
import core_io_reference as C
import kit_contract as K
import signoff as S
from test_kit_contract import write_kit


def vehicle(tmp_path):
    kd=write_kit(tmp_path/"kit")
    ref=dict(kind="plan_declared",tt=750.,ff=660.,basis="pre-build DME total internal latency",
             source="results/parent_trunk_plan.json")
    core=dict(clock_contract=dict(kind="hard_core_latency",io_reference_ps=ref))
    (kd/"core.json").write_text(json.dumps(core))
    (kd/"boundary_guard_context.json").write_text(json.dumps(dict(source_core_json="core.json")))
    for name in ("config.mk","constraint.sdc","grt_pre.tcl","sdc_lint.json","clock_binding.json","freeze.json"):
        p=kd/name;s=p.read_text().replace("250.0000","750.0000").replace("202.5000","660.0000")
        s=s.replace("250.0","750.0").replace("202.5","660.0");p.write_text(s)
    f=kd/"freeze.json";d=json.loads(f.read_text());d["io_reference_ps"]=dict(ref);f.write_text(json.dumps(d))
    return kd,ref


def test_consistent_planned_reference_and_measured_contract(tmp_path):
    kd,ref=vehicle(tmp_path)
    assert K.corner_modes(kd)[0]==[] and K.ff_binding(kd)[0]==[]
    got=S.hard_core_latency_contract(dict(kit=str(kd)))
    assert got["io_reference_ps"]==ref
    assert got["kind"]=="hard_core_latency"  # actual measured I remains a separate sign-off output


@pytest.mark.parametrize("name",["config.mk","constraint.sdc","sdc_lint.json","clock_binding.json","freeze.json"])
def test_each_stale_tt_reference_fails_preflight_and_signoff(tmp_path,name):
    kd,_=vehicle(tmp_path);p=kd/name;p.write_text(p.read_text().replace("750.0","250.0"))
    assert K.ff_binding(kd)[0]
    with pytest.raises(ValueError,match="inconsistent typed"):
        S.hard_core_latency_contract(dict(kit=str(kd)))


def test_ff_only_cli_shift_is_rejected(tmp_path):
    _,ref=vehicle(tmp_path)
    C.validate_ff_override(ref,660.)
    with pytest.raises(ValueError,match="FF CLI override"):
        C.validate_ff_override(ref,202.5)


@pytest.mark.parametrize("change",[dict(kind="measured"),dict(tt=float("nan")),dict(ff=True),dict(source="")])
def test_untyped_nonfinite_or_missing_plan_source_fails(tmp_path,change):
    kd,_=vehicle(tmp_path);p=kd/"core.json";d=json.loads(p.read_text())
    d["clock_contract"]["io_reference_ps"].update(change);p.write_text(json.dumps(d))
    assert K.ff_binding(kd)[0]


def test_mm_ff_mode_remains_corner_specific(tmp_path):
    kd,_=vehicle(tmp_path)
    with (kd/"config.mk").open("a") as f:f.write("\nexport OT_HOLD_MM = 1\nexport OT_MM_SETUP_CORNER = tc\nexport OT_MM_FF_SDC = /work/ff.sdc\n")
    (kd/"grt_pre.tcl").write_text("")
    (kd/"ff.sdc").write_text("set_clock_latency -source 660.0000 [get_clocks vclk]\n")
    assert K.corner_modes(kd)[0]==[]
    (kd/"ff.sdc").write_text("set_clock_latency -source 750.0000 [get_clocks vclk]\n")
    assert K.corner_modes(kd)[0]


def test_original_untagged_kit_stays_fixed_target(tmp_path):
    kd=write_kit(tmp_path/"old")
    assert C.load(kd) is None and K.ff_binding(kd)[0]==[] and K.corner_modes(kd)[0]==[]
    p=kd/"config.mk";p.write_text(p.read_text().replace("250.0000","750.0000"))
    assert K.ff_binding(kd)[0]


def test_existing_generator_text_precision_is_preserved(tmp_path):
    kd,_=vehicle(tmp_path)
    p=kd/"config.mk";p.write_text(p.read_text().replace("750.0000","750.0005"))
    assert C.REFERENCE_TOL_PS==K.TOL
    assert K.ff_binding(kd)[0]==[]
