"""HEAD-94 11-11 (COORD): kit_contract compares vclk latency to the PLAN's own insertion (sdc_lint.json / clock_binding.json),
falling back to the 12.3 default only when the plan gives none.  False advisories hide real ones."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_contract as KC  # noqa: E402
from test_kit_contract import write_kit  # noqa: E402


def _retarget(kd, tt, ff, lint=True, binding=True):
    cfg = (kd / "config.mk").read_text()
    cfg = re.sub(r"OT_VCLK_TT = [\d.]+", f"OT_VCLK_TT = {tt:.4f}", cfg)
    cfg = re.sub(r"OT_VCLK_FF = [\d.]+", f"OT_VCLK_FF = {ff:.4f}", cfg)
    (kd / "config.mk").write_text(cfg)
    sdc = (kd / "constraint.sdc").read_text()
    (kd / "constraint.sdc").write_text(re.sub(r"-source 250\.0000", f"-source {tt:.4f}", sdc))
    g = (kd / "grt_pre.tcl").read_text()
    (kd / "grt_pre.tcl").write_text(g.replace("202.5", f"{ff:g}"))
    fz = kd / "freeze.json"
    if fz.is_file():
        j = json.loads(fz.read_text())
        for k in ("insertion_ff_ps", "ff_bound_ps"):
            if k in j:
                j[k] = ff
        fz.write_text(json.dumps(j))
    if lint:
        (kd / "sdc_lint.json").write_text(json.dumps(dict(insertion_ps=tt, insertion_ff_ps=ff, insertion_tol_ps=40.0)))
    else:
        (kd / "sdc_lint.json").unlink()
    if binding:
        (kd / "clock_binding.json").write_text(json.dumps(dict(insertion_ps=dict(tt=tt, ff=ff))))
    else:
        (kd / "clock_binding.json").unlink()


def test_plan_insertion_450_is_not_flagged(tmp_path):
    kd = tmp_path / "k"; write_kit(kd); _retarget(kd, 450.0, 342.0)
    assert KC.corner_modes(kd)[0] == []
    assert KC.ff_binding(kd)[0] == []


def test_kit_vclk_off_the_plan_insertion_still_fails(tmp_path):
    kd = tmp_path / "k"; write_kit(kd); _retarget(kd, 450.0, 342.0)
    (kd / "constraint.sdc").write_text((kd / "constraint.sdc").read_text().replace("450.0000", "250.0000"))
    assert any("not exactly one line = TT 450" in e for e in KC.corner_modes(kd)[0])
    cfg = (kd / "config.mk").read_text().replace("OT_VCLK_FF = 342.0000", "OT_VCLK_FF = 202.5000")
    (kd / "config.mk").write_text(cfg)
    assert any("OT_VCLK_FF" in e and "342" in e for e in KC.ff_binding(kd)[0])


def test_plan_without_insertion_falls_back_to_12_3_default(tmp_path):
    kd = tmp_path / "k"; write_kit(kd)
    (kd / "sdc_lint.json").write_text(json.dumps(dict(period_ps=833.0)))
    (kd / "clock_binding.json").write_text(json.dumps(dict()))
    assert KC._plan_reference(kd) is None
    assert KC.corner_modes(kd)[0] == []                       # fixture is at 250 / 202.5
    (kd / "constraint.sdc").write_text((kd / "constraint.sdc").read_text().replace("250.0000", "450.0000"))
    assert any("= TT 250" in e for e in KC.corner_modes(kd)[0])   # the default still bites without a plan value


def test_clock_binding_alone_supplies_the_reference(tmp_path):
    kd = tmp_path / "k"; write_kit(kd); _retarget(kd, 450.0, 342.0, lint=False)
    assert KC._plan_reference(kd) == (450.0, 342.0)
    assert KC.corner_modes(kd)[0] == []
