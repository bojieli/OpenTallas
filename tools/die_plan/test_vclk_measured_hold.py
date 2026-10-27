"""S81-ECO-2 10-27: FF hold is repaired in the frame the kit is signed off in (vclk_ref.py decision shared with
signoff.py; vclk_measured_hold.tcl in grt_post.tcl; sdc_lint / kit_preflight check).
    python3 -m pytest -q tools/die_plan/test_vclk_measured_hold.py"""
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sdc_lint  # noqa: E402
import signoff  # noqa: E402
import vclk_ref  # noqa: E402


def _kit(tmp, *, ff=202.5, contract=None, ctx=True, core=True, step=True):
    kd = Path(tmp)
    (kd / "config.mk").write_text(f"export OT_VCLK_TT = 250.0000\nexport OT_VCLK_FF = {ff:.4f}\n")
    (kd / "sdc_lint.json").write_text(json.dumps(dict(insertion_ps=250.0, insertion_ff_ps=ff, insertion_tol_ps=40.0)))
    if ctx:
        (kd / "boundary_guard_context.json").write_text(json.dumps(dict(source_core_json="core.json")))
    if core:
        (kd / "core.json").write_text(json.dumps(dict(clock_contract=contract) if contract else {}))
    if step:
        for f in ("vclk_measured_hold.tcl", "vclk_ref.py", "grt_post.tcl"):
            shutil.copyfile(HERE / f, kd / f)
    return kd


def test_reference_rebind_bound_sdc(tmp_path):
    (tmp_path / "a").mkdir()
    a = _kit(tmp_path / "a")
    assert vclk_ref.ff_reference(a) == dict(ref="rebind", ff_bound=202.5, tol=40.0)
    (tmp_path / "b").mkdir()
    b = _kit(tmp_path / "b", contract=dict(kind="hard_core_latency"))
    assert vclk_ref.ff_reference(b)["ref"] == "bound-ff"
    (tmp_path / "c").mkdir()
    c = _kit(tmp_path / "c")
    (c / "sdc_lint.json").write_text(json.dumps(dict(insertion_ps=250.0)))
    assert vclk_ref.ff_reference(c)["ref"] == "sdc"


def test_reference_fails_closed_on_missing_core_json(tmp_path):
    kd = _kit(tmp_path, core=False)
    with pytest.raises(vclk_ref.RefError):
        vclk_ref.ff_reference(kd)
    assert vclk_ref.main([str(kd)]) == 2


def test_contract_decision_matches_signoff(tmp_path):
    for i, contract in enumerate((None, dict(kind="hard_core_latency"), dict(kind="other"))):
        d = tmp_path / str(i); d.mkdir()
        kd = _kit(d, contract=contract)
        assert (vclk_ref.hard_core_latency_contract(kd) is None) == \
            (signoff.hard_core_latency_contract(dict(kit=str(kd))) is None)
    assert vclk_ref.hard_core_latency_contract(None) is None


def test_check_rebind_kit_without_measured_step_fails(tmp_path):
    kd = _kit(tmp_path, step=False)
    (kd / "grt_post.tcl").write_text("ot_vclk_bind tt\n")   # pre-S81-ECO-2 copy
    err = sdc_lint.ff_binding_errors(kd, json.loads((kd / "sdc_lint.json").read_text()))
    assert len(err) == 1 and "rebind" in err[0] and "vclk_measured_hold.tcl" in err[0]


def test_check_rebind_kit_with_step_passes_and_bound_kit_exempt(tmp_path):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    kd = _kit(tmp_path / "a")
    assert sdc_lint.ff_binding_errors(kd, json.loads((kd / "sdc_lint.json").read_text())) == []
    hb = _kit(tmp_path / "b", contract=dict(kind="hard_core_latency"), step=False)
    assert sdc_lint.ff_binding_errors(hb, json.loads((hb / "sdc_lint.json").read_text())) == []


def test_grt_post_runs_measured_hold_before_tt_restore():
    t = (HERE / "grt_post.tcl").read_text()
    i, j = t.index("ot_vclk_measured_hold"), t.index("ot_vclk_bind tt")
    assert i < j and t.index("vclk_measured_hold.tcl") < i
    assert t.index("ot_vclk_bind tt") < t.index("ot_pg_connect_all grt_post")   # new hold cells get PG


def test_measured_selection_mirrors_signoff():
    """the in-flow mean uses signoff.FF_VCLK_TCL's register selection and arrival source."""
    m = (HERE / "vclk_measured_hold.tcl").read_text()
    for key in ("all_registers -clock_pins", "all_registers -async_pins", "all_registers -data_pins",
                "get_fanout -from $din -flat -endpoints_only -trace_arcs all",
                "get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all",
                "ot_cf_wire $p [lindex $cl 0]", "get_property $p arrival_max_rise", "ot_cf_refresh"):
        assert key in m, key
        assert key.replace("$din", "$so_din") in signoff.FF_VCLK_TCL, key
    assert "set_clock_latency -source $mean" in m
    assert re.search(r"abs\(\$mean - \$ffb\) > \$tol", m)            # band check, fail closed
    assert "repair_timing -hold -hold_margin $hm" in m                 # margin unchanged (kit OT_HOLD_FF_MARGIN)


def test_generators_stage_the_step():
    for f in ("gen_phys.py", "core_flow.py"):
        s = (HERE / f).read_text()
        assert "\"vclk_measured_hold.tcl\", \"vclk_ref.py\"" in s, f
