"""KW-FIX-34-SIG (COORD 2026-11-08 02:06, OWNER 11-03 'insertion band -> die STA'): a hard_core_latency contract kit
times TT IO against the routed TT pin-register mean (rebind basis); FF stays bound-ff (declared 202.5).  Every other
kit keeps its policy and session text unchanged."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signoff  # noqa: E402
from test_signoff import GOOD_SDC, record  # noqa: E402

HCL = dict(kind="hard_core_latency", ruling="COORD 10-24")
TT_REF = "applied mode pin_flop_mean clock vclk latency_ps 476.090000 samples 9198 missing 0 clocks 1 forwarded_excluded 0"
FF_REF = "applied mode bound_ff clock vclk latency_ps 202.500000"


# ---- session text ----------------------------------------------------------------------------------------------------
def test_tt_rebind_session_with_bound_ff():
    tt = signoff.session_tcl("tt", [], None, ff_vclk="bound-ff", ff_bound_ps=202.5, tt_vclk="rebind")
    assert "mode pin_flop_mean" in tt and "mode bound_ff" not in tt
    ff = signoff.session_tcl("ff", [], None, ff_vclk="bound-ff", ff_bound_ps=202.5, tt_vclk="rebind")
    # FF unchanged by the TT-only rebind: still the declared bound, no measured rebind
    assert ff == signoff.session_tcl("ff", [], None, ff_vclk="bound-ff", ff_bound_ps=202.5)
    assert "set_clock_latency -source 202.500000" in ff and "mode pin_flop_mean" not in ff


@pytest.mark.parametrize("ff_vclk", signoff.VCLK_MODES)
@pytest.mark.parametrize("corner", ("tt", "ff", "ss"))
def test_default_tt_vclk_session_byte_identical(corner, ff_vclk):
    kw = dict(ff_vclk=ff_vclk, ff_bound_ps=202.5)
    assert signoff.session_tcl(corner, [], None, tt_vclk="sdc", **kw) == signoff.session_tcl(corner, [], None, **kw)


def test_tt_vclk_rejects_unknown():
    with pytest.raises(ValueError):
        signoff.session_tcl("tt", [], None, tt_vclk="bound-ff")


# ---- verdict ---------------------------------------------------------------------------------------------------------
def _hcl_record(tt_vclk, sdc_wns=-147.74, std_wns=12.0, tt_ref=TT_REF):
    pol = dict(ff_vclk="bound-ff", ff_vclk_bound_ps=202.5, insertion_bound=None)
    if tt_vclk:
        pol["tt_vclk"] = tt_vclk
    rec = record(tt_setup=std_wns, policy=pol)
    rec["corners"]["tt"].update(sdc_wns_max=sdc_wns, ff_vclk_reference=tt_ref)
    rec["corners"]["ff"]["ff_vclk_reference"] = FF_REF
    return rec


def test_hcl_tt_rebind_verdict_uses_measured_reference():
    rec = _hcl_record("rebind")
    signoff.evaluate(rec)
    st = rec["checks"]["setup_tt"]
    assert st["verdict"] == "PASS" and st["wns_ps"] == 12.0 and st["sdc_wns_ps"] == -147.74
    assert st["vclk_reference"] == TT_REF
    assert rec["checks"]["hold_ff"]["verdict"] == "PASS"                        # FF still bound-ff 202.5
    assert rec["checks"]["hold_ff"]["ff_vclk_reference"] == FF_REF
    # a real miss against the measured reference still fails
    rec = _hcl_record("rebind", std_wns=-3.0)
    signoff.evaluate(rec)
    assert rec["checks"]["setup_tt"]["verdict"] == "FAIL"
    # the rebind did not apply in the TT session -> NOT RUN (never a silent fall back to the SDC vclk)
    rec = _hcl_record("rebind", tt_ref="unavailable mode pin_flop_mean vclks 2 samples 0 missing 0")
    signoff.evaluate(rec)
    assert rec["checks"]["setup_tt"]["verdict"] == "NOT RUN"


def test_bound_ff_without_tt_vclk_unchanged():
    """records without policy.tt_vclk (old hcl records, every non-contract kit) keep the SDC TT verdict"""
    rec = _hcl_record(None)
    signoff.evaluate(rec)
    assert rec["checks"]["setup_tt"]["verdict"] == "FAIL" and rec["checks"]["setup_tt"]["wns_ps"] == -147.74
    assert "vclk_reference" not in rec["checks"]["setup_tt"]


# ---- CLI policy selection --------------------------------------------------------------------------------------------
def _run(tmp_path, monkeypatch, contract, extra=()):
    kit = tmp_path / "kit"
    kit.mkdir(exist_ok=True)
    (kit / "constraint.sdc").write_text(GOOD_SDC)
    ctx = kit / "sdc_lint.json"
    ctx.write_text(json.dumps(dict(insertion_ps=250, insertion_ff_ps=202.5, insertion_tol_ps=40)))
    monkeypatch.setattr(signoff, "find_base", lambda _: kit)
    monkeypatch.setattr(signoff, "discover", lambda *a, **kw: dict(
        sdc=str(kit / "constraint.sdc"), sdc_lint_ctx=str(ctx), design="blk"))
    monkeypatch.setattr(signoff, "require_signoff_bundle", lambda: None)
    monkeypatch.setattr(signoff, "hard_core_latency_contract", lambda _: contract)
    monkeypatch.setattr(signoff, "_git_head", lambda: "test")
    seen = {}

    def corner(c, disc, out, image, docker, dry, ff_vclk, *args):
        seen[c] = signoff.session_tcl(c, [], None, ff_vclk=ff_vclk, ff_bound_ps=disc.get("ff_bound_ps"),
                                      tt_vclk=disc.get("tt_vclk", "sdc"))
        seen["ff_vclk"], seen["tt_vclk"], seen["ff_bound_ps"] = ff_vclk, disc.get("tt_vclk"), disc.get("ff_bound_ps")
        return {}
    monkeypatch.setattr(signoff, "run_corner", corner)
    assert signoff.main(["run", "--run-dir", str(kit), "--out", str(tmp_path / "out"), "--dry", *extra]) == 0
    return seen


def test_cli_hcl_kit_tt_rebind_ff_bound(tmp_path, monkeypatch):
    s = _run(tmp_path, monkeypatch, dict(HCL))
    assert s["ff_vclk"] == "bound-ff" and s["ff_bound_ps"] == 202.5 and s["tt_vclk"] == "rebind"
    assert "mode pin_flop_mean" in s["tt"] and "mode bound_ff" not in s["tt"]
    assert "set_clock_latency -source 202.500000" in s["ff"] and "mode pin_flop_mean" not in s["ff"]


def test_cli_hcl_kit_tt_opt_out(tmp_path, monkeypatch):
    s = _run(tmp_path, monkeypatch, dict(HCL), ["--tt-vclk", "sdc"])
    assert s["ff_vclk"] == "bound-ff" and s["tt_vclk"] is None and "mode pin_flop_mean" not in s["tt"]


def test_cli_typed_io_reference_keeps_declared_tt(tmp_path, monkeypatch):
    cc = dict(HCL, io_reference_ps=dict(kind="plan_declared", tt=250.0, ff=202.5, basis="plan", source="t"))
    s = _run(tmp_path, monkeypatch, cc)
    assert s["ff_vclk"] == "bound-ff" and s["tt_vclk"] is None and "mode pin_flop_mean" not in s["tt"]


def test_cli_non_contract_kit_unchanged(tmp_path, monkeypatch):
    s = _run(tmp_path, monkeypatch, None)            # die-plan kit with a per-corner binding: rebind both corners
    assert s["ff_vclk"] == "rebind" and s["tt_vclk"] is None
    assert s["tt"] == signoff.session_tcl("tt", [], None, ff_vclk="rebind")
