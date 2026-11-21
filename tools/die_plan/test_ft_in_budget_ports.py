"""QC-PLAN-R8 11-20: plan budgets.ft_in_budget_ps sets the CBC registered-sender seam budget per receiver ft input
port (ps, or {"seam_um": L} -> 50 + 0.65 x min(L, hop cap)); absent key = the die-wide 245 ps, byte-identical kits."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cbc_rules as CBC  # noqa: E402
import gen_phys  # noqa: E402
import landing_contract as LC  # noqa: E402
import schema  # noqa: E402
import sdc_lint  # noqa: E402
from test_ring_hold_fall import _ft_port, _ft_ring_plan, _ring_max  # noqa: E402
from test_sdc_lint import PAIR, _errs  # noqa: E402

DEF = CBC.SEAM_CLKQ_PS + CBC.SEAM_PS_PER_UM * CBC.REACH_UM_PER_HOP


def test_cbc_rules_default_and_overrides(monkeypatch):
    assert CBC.ft_in_budget_ps() == DEF
    assert CBC.ft_in_budget_ps(port="cws2_i", tn="t", budgets={}) == DEF
    b = {"ft_in_budget_ps": {"cws1_i": {"seam_um": 133.1}, "cws2_i": 195.3, "t/cws2_i": 180.0, "x_i": {"seam_um": 900}}}
    assert abs(CBC.ft_in_budget_ps(port="cws1_i", budgets=b) - 136.515) < 1e-9
    assert CBC.ft_in_budget_ps(port="cws2_i", tn="u", budgets=b) == 195.3
    assert CBC.ft_in_budget_ps(port="cws2_i", tn="t", budgets=b) == 180.0     # type-scoped key wins
    assert CBC.ft_in_budget_ps(port="x_i", budgets=b) == DEF                   # seam priced at most at the hop cap
    assert CBC.ft_in_budget_ps(port="other_i", budgets=b) == DEF
    assert CBC.ft_in_budget_ps(budgets=b) == DEF                               # no port = die-wide budget
    monkeypatch.setenv("OT_FT_IN_BUDGET", "fixed")
    assert CBC.ft_in_budget_ps(port="cws2_i", budgets=b) is None


def _pair(ov=None):
    raw = copy.deepcopy(PAIR)
    if ov is not None:
        raw.setdefault("budgets", {})["ft_in_budget_ps"] = ov
    P = schema.Plan(raw)
    tn = next(t for t in P.types if P.types[t].get("ft_slots") and any(p["type"] == t for p in P.parts.values()))
    return raw, P, tn


def test_kit_sdc_default_byte_identical_and_override_per_port():
    raw0, P0, tn = _pair()
    _r, Pe, _t = _pair({})
    pins = gen_phys.type_pins(P0, tn)
    base = gen_phys.sdc(P0, tn, pins)
    assert gen_phys.sdc(Pe, tn, pins) == base                                  # empty map = unchanged
    slots = [s["name"] for s in P0.types[tn]["ft_slots"]]
    port = slots[0] + "_i"
    _r, Pn, _t = _pair({"unrelated_i": 100.0})
    assert gen_phys.sdc(Pn, tn, pins) == base                                  # no matching port = unchanged
    raw, P, _t = _pair({port: {"seam_um": 100.0}})
    assert schema.validate(raw) == []
    txt = gen_phys.sdc(P, tn, pins)
    exp = gen_phys.t_lib(CBC.seam_budget_ps(100.0))
    tw = gen_phys.t_lib(gen_phys.tap_window_io_shift(P, tn)[0])
    assert f"set_input_delay -max {exp + tw:.4f} -clock vclk [get_ports {{{port}[*]}}]" in txt
    if len(slots) > 1:
        dflt = gen_phys._ft_in_max_ps(P, gen_phys.t_lib((1 - gen_phys.ft_hop_in_share(P)) * P.die["period_ps"]))
        assert f"set_input_delay -max {dflt + tw:.4f} -clock vclk [get_ports {{{slots[1]}_i[*]" in txt
    ctx = sdc_lint.kit_context(P, tn)
    assert abs(ctx["io_floor_ps"][port] - exp) < 1e-9                        # lint floor follows the plan key
    assert _errs(txt, ctx) == []


def test_ring_input_sdc_override(monkeypatch):
    P0, tn, b, raw = _ft_ring_plan(350.0)
    _ft_port(monkeypatch, b)
    base = LC.ring_input_sdc(P0, tn)
    raw = copy.deepcopy(raw)
    raw.setdefault("budgets", {})["ft_in_budget_ps"] = {f"{tn}/{b}": 195.3}
    P = schema.Plan(raw)
    assert abs(_ring_max(P, tn, b) - gen_phys.t_lib(195.3)) < 1e-6
    assert abs(sdc_lint.kit_context(P, tn)["io_floor_ps"][b] - gen_phys.t_lib(195.3)) < 1e-6
    raw["budgets"]["ft_in_budget_ps"] = {"other_type/" + b: 100.0}
    assert LC.ring_input_sdc(schema.Plan(raw), tn) == base


def test_schema_accepts_and_rejects():
    raw, _P, _t = _pair({"cws1_i": {"seam_um": 133.1}, "sle_ctl__cla4f6f12f/cws2_i": 195.3})
    assert schema.validate(raw) == []
    for bad in ({"cws1_i": 0}, {"cws1_i": {"seam": 1}}, {"cws1_i": "x"}, {"cws1_i": {"seam_um": 1, "x": 2}}):
        raw, _P, _t = _pair(bad)
        assert schema.validate(raw), bad
