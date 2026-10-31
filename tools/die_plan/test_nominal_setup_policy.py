"""OWNER 12.24b/c (2026-10-31): nominal SETUP sign-off -- the 60 ps setup clock uncertainty -> 0 in the kit SDC, in
sdc_lint and in-session in signoff.py (so a RE-SIGN of an old 60 / 25 SDC is timed at setup 0); the HOLD side is
unchanged (25 ps hold uncertainty, +10 ps kit hold-repair margin).  Legacy switch OT_MARGIN_POLICY=legacy /
signoff.py run --margin-policy legacy restores setup 60 (A/B, margin reports).
    python3 -m pytest -q tools/die_plan/test_nominal_setup_policy.py"""
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import core_flow  # noqa: E402
import gen_phys  # noqa: E402
import schema  # noqa: E402
import sdc_lint  # noqa: E402
import signoff as so  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
OLD_SDC = ("create_clock -name clk -period 833.0000 [get_ports clk]\n"
           "set_clock_uncertainty 60.0000 -setup [all_clocks]\n"
           "set_clock_uncertainty 25.0000 -hold [all_clocks]\n"
           "set_clock_uncertainty -from [get_clocks vclk] -to [get_clocks clk] -setup 30.0000\n")


@pytest.fixture(autouse=True)
def _nominal(monkeypatch):
    monkeypatch.delenv(sdc_lint.MARGIN_POLICY_ENV, raising=False)


def _kit():
    P = schema.Plan(TINY)
    tn = next(t for t in P.types if not P.types[t].get("hard"))
    return gen_phys.sdc(P, tn, gen_phys.type_pins(P, tn)), sdc_lint.kit_context(P, tn)


def _unc(txt):
    return {k: [float(v) for v in re.findall(rf"set_clock_uncertainty {pat}", txt)]
        for k, pat in (("setup", r"([0-9.]+) -setup \[all_clocks\]"), ("hold", r"([0-9.]+) -hold \[all_clocks\]"),
                       ("setup_seam", r"-from \[get_clocks \w+\] -to \[get_clocks \w+\] -setup ([0-9.]+)"),
                       ("hold_seam", r"-from \[get_clocks \w+\] -to \[get_clocks \w+\] -hold ([0-9.]+)"))}


def test_policy_constants_setup_0_hold_25_separate():
    assert sdc_lint.margin_policy() == "nominal"
    assert sdc_lint.policy_uncertainty() == (0.0, 25.0)
    assert sdc_lint.policy_uncertainty("legacy") == (60.0, 25.0)
    assert sdc_lint.NOMINAL_UNC_HOLD_PS == sdc_lint.LEGACY_UNC_HOLD_PS == 25.0   # hold side unchanged
    with pytest.raises(ValueError):
        sdc_lint.margin_policy("relaxed")


def test_kit_sdc_setup_0_hold_25_by_default_and_lints():
    txt, ctx = _kit()
    u = _unc(txt)
    assert u == dict(setup=[0.0], hold=[25.0], setup_seam=[0.0, 0.0], hold_seam=[12.5, 12.5])
    assert ctx["unc_setup_ps"] == 0.0 and ctx["unc_hold_ps"] == 25.0
    assert "margin policy nominal" in txt
    assert sdc_lint.lint(txt, **ctx) == []


def test_sdc_lint_nominal_rejects_a_60_setup_sdc():
    txt, ctx = _kit()
    bad = txt.replace("set_clock_uncertainty 0.0000 -setup [all_clocks]", "set_clock_uncertainty 60.0000 -setup [all_clocks]")
    assert bad != txt
    assert any("setup uncertainty on clk = 60 ps, sign-off policy 0 ps" in e for e in sdc_lint.lint(bad, **ctx))
    # lint() without explicit values uses the policy at call time
    ctx2 = {k: v for k, v in ctx.items() if k not in ("unc_setup_ps", "unc_hold_ps")}
    assert sdc_lint.lint(txt, **ctx2) == []


def test_legacy_switch_reproduces_60_25(monkeypatch):
    monkeypatch.setenv(sdc_lint.MARGIN_POLICY_ENV, "legacy")
    txt, ctx = _kit()
    assert _unc(txt) == dict(setup=[60.0], hold=[25.0], setup_seam=[30.0, 30.0], hold_seam=[12.5, 12.5])
    assert ctx["unc_setup_ps"] == 60.0 and sdc_lint.lint(txt, **ctx) == []
    assert so.unc_policy_tcl() == ""                                   # legacy: golden SDC as written
    rec = so.margin_policy_record(None, OLD_SDC)
    assert rec["uncertainty_setup_ps"] == 60.0 and "sdc_uncertainty_overridden" not in rec


def test_landing_window_unchanged():
    assert sdc_lint.LANDING_WINDOW_SETUP_PS == 60.0


def test_signoff_session_overrides_setup_after_read_sdc():
    t = so.session_tcl("tt", [], True)
    i_sdc, i_unc = t.index("read_sdc /sdc/golden.sdc"), t.index("so_unc_apply setup 0 0.5")
    assert i_sdc < i_unc < t.index("so_timing SDC")
    assert "so_unc_apply hold" not in t                                # hold side not touched
    assert "so UNC_POLICY nominal setup 0 hold 25 kinds setup errors" in t
    assert "so_unc_apply" not in so.session_tcl("tt", [], True, margin_policy="legacy")


def test_signoff_records_old_sdc_overridden():
    rec = so.margin_policy_record(None, OLD_SDC)
    assert rec["margin_policy"].startswith("nominal OWNER 12.24b")
    assert rec["uncertainty_setup_ps"] == 0.0 and rec["uncertainty_hold_ps"] == 25.0
    assert rec["sdc_uncertainty_ps"] == dict(setup=60.0, hold=25.0)
    assert rec["sdc_uncertainty_overridden"] == dict(setup=dict(sdc=60.0, signoff=0.0, changed=True))
    assert "OT_MARGIN_POLICY=legacy" in rec["margin_policy_switch"] and "--margin-policy legacy" in rec["margin_policy_switch"]


def test_restoring_hold_constant_alone_is_independent(monkeypatch):
    monkeypatch.setattr(sdc_lint, "NOMINAL_UNC_HOLD_PS", 0.0)
    assert so.overridden_kinds() == ("setup", "hold")
    assert "so_unc_apply hold 0 0.5" in so.unc_policy_tcl()


def test_corner_parse_and_fail_closed_when_override_missing():
    log = ("SO UNC_POLICY nominal setup 0 hold 25 kinds setup errors 0\nSO DONE 1\nSO SDC_WNS_MAX 12.5\n")
    c = so.corner_result(so.parse_session(log))
    assert c["unc_policy"] == dict(policy="nominal", setup_ps=0.0, hold_ps=25.0, errors=0.0)
    pol = so.margin_policy_record(None, OLD_SDC)

    def setup_verdict(corner):
        rec = dict(policy=dict(pol, ff_vclk="sdc"), corners=dict(tt=corner), sdc_lint={}, face_guard={}, route={})
        try:
            so.evaluate(rec)
        except Exception:               # noqa: BLE001  other record checks need more inputs; setup_tt is filled first
            pass
        return rec.get("checks", {}).get("setup_tt", {}).get("verdict")

    import copy
    ok = setup_verdict(copy.deepcopy(c))
    missing = copy.deepcopy(c)
    missing.pop("unc_policy")
    bad = copy.deepcopy(c)
    bad["unc_policy"]["errors"] = 1.0
    if ok is None:
        pytest.skip("evaluate() needs a fuller record in this checkout")
    assert ok == "PASS"
    assert setup_verdict(missing) == "NOT RUN" and setup_verdict(bad) == "NOT RUN"


def test_run_sdc_lint_derived_accepts_old_60_25_sdc(tmp_path, monkeypatch):
    monkeypatch.setenv(sdc_lint.MARGIN_POLICY_ENV, "legacy")
    txt, ctx = _kit()
    monkeypatch.delenv(sdc_lint.MARGIN_POLICY_ENV)
    (tmp_path / "c.sdc").write_text(txt)
    ports = dict(clock_ports=ctx["clock_ports"], inputs=ctx["inputs"], outputs=ctx["outputs"])
    r = so.run_sdc_lint(dict(sdc=str(tmp_path / "c.sdc"), sdc_source="kit"), ports)
    assert "SDC contract 60/25" in r["mode"]
    assert not any("uncertainty" in e for e in r["errors"])


def test_hold_repair_margin_default_stays_10():
    assert core_flow.HOLD_FF_MARGIN_DEFAULT == 10.0
    assert gen_phys.HOLD_FF_MARGIN_DEFAULT == 10.0
    assert 'a3.add_argument("--hold-ff-margin", type=float, default=10.0' in (HERE / "gen.py").read_text()
    assert '"export HOLD_SLACK_MARGIN = 5"' in (HERE / "gen_phys.py").read_text()


@pytest.mark.parametrize("rel", ["physical/die_plan/qwen_kvsys/cores/harden/gen_core_kit_kv.py",
                                 "physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py",
                                 "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py"])
def test_die_core_generators_follow_the_policy(rel):
    f = REPO / rel
    if not f.is_file():
        pytest.skip(f"{rel} not checked out")
    spec = importlib.util.spec_from_file_location("gen_mod_" + f.stem, f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert (m.UNC_SETUP_PS, m.UNC_HOLD_PS) == sdc_lint.policy_uncertainty() == (0.0, 25.0)


def test_hbm_generator_source_reads_the_policy():
    f = REPO / "physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py"
    if not f.is_file():
        pytest.skip("not checked out")
    src = f.read_text()
    assert "UNC_SETUP_PS, UNC_HOLD_PS = _policy_unc()" in src and "= 60.0, 25.0, 0.5, 2.0" not in src
