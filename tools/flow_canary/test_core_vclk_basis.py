"""The canary honours the canonical typed-core FF contract without waiving timing gates."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canary as C


def fixture(tmp_path):
    kit = tmp_path / "kit"
    kit.mkdir()
    def write(name, obj):
        (kit / name).write_text(json.dumps(obj))
    (kit / "config.mk").write_text("export OT_VCLK_TT = 250\nexport OT_VCLK_FF = 202.5\n")
    (kit / "constraint.sdc").write_text("set_clock_latency -source 250 [get_clocks vclk]\n")
    write("clock_binding.json", dict(insertion_ps=dict(tt=250, ff=202.5), insertion_tol_ps=40))
    write("boundary_guard_context.json", dict(schema="opentallas.core_boundary_guard_context.v1", source_core_json="core.json"))
    write("core.json", dict(clock_contract=dict(kind="hard_core_latency")))
    write("sdc_lint.json", dict(insertion_ff_ps=202.5))
    so = dict(verdict="NOT SIGNED", policy=dict(ff_vclk="bound-ff", ff_vclk_bound_ps=202.5),
              checks=dict(clock=dict(core_latency_contract="hard_core_latency"),
                          setup_tt=dict(wns_ps=-57.66), hold_ff=dict(wns_ps=-1.01)),
              corners={c:dict(insertion_pinflops=dict(mean=m),
                             ff_vclk_reference="applied mode bound_ff clock vclk latency_ps 202.500000")
                       for c,m in (("tt",288.8),("ff",231.36))})
    return kit, so, write


def test_typed_core_basis_accepts_declared_applied_ff_but_not_timing_regression(tmp_path):
    kit, so, _ = fixture(tmp_path)
    assert C.vclk_basis(kit, so)["verdict"] == "PASS"
    golden = dict(verdict="SIGNED", setup_tt_wns=36.61, hold_ff_wns=-5.92)
    assert C.chk_signoff(so, golden, 15)["verdict"] == "FAIL"


@pytest.mark.parametrize("bad", ["no_manifest", "wrong_kind", "wrong_schema", "missing_declared_bound",
                                  "wrong_signoff_bound", "missing_applied", "wrong_applied", "missing_record_contract",
                                  "outside_mean_bound", "nan_declared_bound", "wrong_reference_clock", "malformed_reference"])
def test_bound_ff_is_not_an_untyped_or_missing_reference_escape(tmp_path, bad):
    kit, so, write = fixture(tmp_path)
    if bad == "no_manifest":
        (kit / "boundary_guard_context.json").unlink()
    elif bad == "wrong_kind":
        write("core.json", dict(clock_contract=dict(kind="partition_tap")))
    elif bad == "wrong_schema":
        write("boundary_guard_context.json", dict(schema="untyped", source_core_json="core.json"))
    elif bad == "missing_declared_bound":
        write("sdc_lint.json", {})
    elif bad == "wrong_signoff_bound":
        so["policy"]["ff_vclk_bound_ps"] = 250
    elif bad == "missing_applied":
        so["corners"]["ff"]["ff_vclk_reference"] = "unavailable mode bound_ff"
    elif bad == "wrong_applied":
        so["corners"]["ff"]["ff_vclk_reference"] = "applied mode bound_ff clock vclk latency_ps 250"
    elif bad == "missing_record_contract":
        so["checks"]["clock"].clear()
    elif bad == "outside_mean_bound":
        so["corners"]["ff"]["insertion_pinflops"]["mean"] = 300
    elif bad == "wrong_reference_clock":
        so["corners"]["ff"]["ff_vclk_reference"] = "applied mode bound_ff clock other latency_ps 202.5"
    elif bad == "malformed_reference":
        so["corners"]["ff"]["ff_vclk_reference"] = "applied mode bound_ff clock vclk latency_ps ..."
    elif bad == "nan_declared_bound":
        write("sdc_lint.json", dict(insertion_ff_ps=float("nan")))
    assert C.vclk_basis(kit, so)["verdict"] == "FAIL"
