"""S81-ECO-2 10-27 measured FF reference, OPT-IN form (FLOW-SHARED-4 rebase of 2f4c07767 + 9891c5f4e7 without
b52ec3248..fba10301d, COORD RM77): vclk_ref.py decision shared with signoff.py; vclk_measured_hold.tcl only through
orfs_hold_mm.tcl when config.mk OT_MM_MEASURED_HOLD = 1.  Defaults (grt_post.tcl, gen_phys.py, core_flow.py, sdc_lint on
an un-opted kit) are unchanged.
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
        for f in ("vclk_measured_hold.tcl", "vclk_ref.py"):
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


def test_defaults_unchanged_rebind_kit_without_opt_in_passes(tmp_path):
    """no OT_MM_MEASURED_HOLD: a 'rebind' kit with or without the files gets no new preflight error (b52ec3248's
    default-on 'rebind kit without the step FAILs' check is NOT part of this branch)"""
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    for kd in (_kit(tmp_path / "a", step=False), _kit(tmp_path / "b")):
        (kd / "grt_post.tcl").write_text("ot_vclk_bind tt\n")
        assert vclk_ref.ff_reference(kd)["ref"] == "rebind"
        assert sdc_lint.ff_binding_errors(kd, json.loads((kd / "sdc_lint.json").read_text())) == []


def test_opt_in_without_two_mode_session_fails_closed(tmp_path):
    kd = _kit(tmp_path)
    (kd / "config.mk").write_text((kd / "config.mk").read_text() + "override export OT_MM_MEASURED_HOLD = 1\n")
    err = sdc_lint.ff_binding_errors(kd, json.loads((kd / "sdc_lint.json").read_text()))
    assert len(err) == 1 and "incomplete" in err[0]


def test_default_flow_files_never_run_the_measured_step():
    """grt_post.tcl / gen_phys.py / core_flow.py: identical to main's default (no measured step, no staging)"""
    assert "vclk_measured_hold" not in (HERE / "grt_post.tcl").read_text()
    for f in ("gen_phys.py", "core_flow.py"):
        s = (HERE / f).read_text()
        assert "vclk_measured_hold" not in s and "vclk_ref.py" not in s, f
    mm = (HERE.parent / "orfs_hold_mm.tcl").read_text()
    i = mm.index("ot_vclk_measured_bind")
    assert 'eq "1"' in mm[mm.rindex("OT_MM_MEASURED_HOLD", 0, i) - 200:i]       # guarded by the opt-in flag


def test_measured_selection_mirrors_signoff():
    """the in-flow mean uses signoff.FF_VCLK_TCL's register selection and arrival source."""
    m = (HERE / "vclk_measured_hold.tcl").read_text()
    for key in ("all_registers -clock_pins", "all_registers -async_pins", "all_registers -data_pins",
                "get_fanout -from $din -flat -endpoints_only -trace_arcs all",
                "get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all",
                "ot_cf_wire $p [lindex $cl 0]", "get_property $p arrival_max_rise", "ot_cf_refresh"):
        assert key.rstrip("]") in m, key
        assert key.replace("$din", "$so_din") in signoff.FF_VCLK_TCL, key
    assert "set_clock_latency -source $mean" in m
    assert re.search(r"abs\(\$mean - \$ffb\) > \$tol", m)            # band check, fail closed
    assert "repair_timing -hold -hold_margin $hm" in m                 # margin unchanged (kit OT_HOLD_FF_MARGIN)
