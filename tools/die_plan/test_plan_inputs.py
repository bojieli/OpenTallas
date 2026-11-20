"""HEAD-CROSSING-1119 11-19 (COORD): plan-relative inputs (hard-core pins_file, native_domains census files) of a plan
composed outside its prep folder resolve from an explicit plan root (die_trial --plan-root / ot_clk inputs.plan_root /
OT_PLAN_ROOT), and a die run names every missing one at plan load -- not one per rerun after the DME stage."""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import plan_inputs as PI  # noqa: E402
import reset_tree as RT  # noqa: E402
import schema  # noqa: E402

TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())
PINS = dict(core="m", pins=[dict(name="rst_n", layer="M4", x=0, y=150)])


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    PI.set_roots([])
    monkeypatch.delenv("OT_PLAN_ROOT", raising=False)
    # no repo-wide physical/die_plan fallback: only the folders under test can supply the table
    (tmp_path / "fake" / "tools" / "die_plan").mkdir(parents=True)
    monkeypatch.setattr(RT, "HERE", tmp_path / "fake" / "tools" / "die_plan")
    yield
    PI.set_roots([])


def _layout(tmp_path):
    """prep/ = the plan's real folder (core_pins/, native_domains/); elsewhere/ = a composed copy of the plan"""
    prep = tmp_path / "prep"
    (prep / "core_pins").mkdir(parents=True)
    (prep / "core_pins" / "m.json").write_text(json.dumps(PINS))
    (prep / "native_domains").mkdir()
    (prep / "native_domains" / "census.json").write_text(json.dumps({"x": 1}))
    raw = copy.deepcopy(TINY)
    raw.setdefault("reset", {}).update(release="wavefront")
    t = raw["partition_types"]["src"]
    t["hard_cores"] = [dict(inst="u_c", module="m", origin_um=[50, 50], outline_um=[200, 300], pins_file="core_pins/m.json")]
    t.setdefault("clock", {})["native_domains"] = dict(census_file="native_domains/census.json",
                                                       children=[dict(inst="u_c", census_file="native_domains/child.json")])
    other = tmp_path / "elsewhere"
    other.mkdir()
    (other / "plan.json").write_text(json.dumps(raw))
    return prep, other / "plan.json", raw


def test_missing_inputs_listed_together_with_folders_tried(tmp_path):
    prep, plan, raw = _layout(tmp_path)
    P = schema.Plan(raw, plan)
    miss = PI.missing(P)
    assert any("pins_file core_pins/m.json" in m for m in miss)
    assert any("census_file native_domains/census.json" in m for m in miss)
    assert any("child u_c census_file native_domains/child.json" in m for m in miss)
    with pytest.raises(PI.PlanInputError) as e:
        PI.check(P)
    assert "3 plan input(s)" in str(e.value) and str(plan.parent) in str(e.value) and "--plan-root" in str(e.value)


def test_plan_root_resolves_pins_and_census(tmp_path):
    prep, plan, raw = _layout(tmp_path)
    (prep / "native_domains" / "child.json").write_text("{}")
    P = schema.Plan(raw, plan)
    PI.set_roots([prep])
    assert PI.missing(P) == []
    PI.check(P)
    assert RT.pin_table_dir(P, "src", raw["partition_types"]["src"]["hard_cores"][0]) == prep
    import native_clock_domains as NCD
    assert NCD._load(P, "native_domains/census.json") == {"x": 1}


def test_env_and_plan_field_roots(tmp_path, monkeypatch):
    prep, plan, raw = _layout(tmp_path)
    (prep / "native_domains" / "child.json").write_text("{}")
    monkeypatch.setenv("OT_PLAN_ROOT", str(prep))
    assert PI.missing(schema.Plan(raw, plan)) == []
    monkeypatch.delenv("OT_PLAN_ROOT")
    raw2 = dict(raw, plan_root=str(prep))
    assert PI.missing(schema.Plan(raw2, plan)) == []


def test_plan_folder_still_wins(tmp_path):
    prep, plan, raw = _layout(tmp_path)
    (prep / "native_domains" / "child.json").write_text("{}")
    (plan.parent / "core_pins").mkdir()
    (plan.parent / "core_pins" / "m.json").write_text(json.dumps(PINS))
    PI.set_roots([prep])
    P = schema.Plan(raw, plan)
    assert RT.pin_table_dir(P, "src", raw["partition_types"]["src"]["hard_cores"][0]) == plan.parent.resolve()


def test_unresolved_pin_table_error_names_folders(tmp_path):
    prep, plan, raw = _layout(tmp_path)
    with pytest.raises(RT.ResetError, match=r"cannot uniquely resolve .*tried .*elsewhere.*--plan-root"):
        RT.pin_table_dir(schema.Plan(raw, plan), "src", raw["partition_types"]["src"]["hard_cores"][0])


def test_die_trial_fails_at_plan_load(tmp_path):
    import die_trial as D
    prep, plan, raw = _layout(tmp_path)
    with pytest.raises(PI.PlanInputError, match="plan input"):
        D.write_kit(str(plan), str(tmp_path / "out"))
    assert not (tmp_path / "out" / "clock").exists()


def test_ot_clk_plan_root_flag():
    sys.path.insert(0, str(HERE.parent / "clk"))
    import ot_clk as O
    c = O.load_config(HERE.parent / "clk" / "configs" / "head.yaml")
    c["inputs"]["plan_root"] = ["/a", "/b"]
    a = O.kit_argv(c, "OUT")
    assert [a[i + 1] for i, x in enumerate(a) if x == "--plan-root"] == ["/a", "/b"]
    c["inputs"]["plan_root"] = 3
    with pytest.raises(O.ConfigError):
        O.kit_argv(c, "OUT")
