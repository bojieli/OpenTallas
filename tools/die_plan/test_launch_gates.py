import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import launch_gates as LG  # noqa: E402


def plan(tmp, ft_x):
    p = tmp / "plan.json"
    t = {"outline_um": [100, 100], "ft_slots": [{"name": "ft0", "regs_um": [[ft_x, 50]], "bit_sites_um": [[ft_x, 50]]}]}
    p.write_text(json.dumps({"partition_types": {"leaf": t}}))
    return str(p)


def test_clean_kit_has_no_lines(tmp_path):
    env = {"OT_KIT_TYPE": "leaf", "OT_KIT_GOAL": "route", "OT_EVENT_TYPES": "leaf"}
    assert LG.lines(tmp_path / "leaf", plan(tmp_path, 50), env) == []


def test_mutants_scope_and_ft_site(tmp_path):
    env = {"OT_KIT_TYPE": "leaf", "OT_KIT_GOAL": "route", "OT_EVENT_TYPES": "other", "OT_WAVE_PLAN_SHA": "a" * 64,
           "OT_KIT_SIGNED": "1"}
    out = LG.lines(tmp_path / "leaf", plan(tmp_path, 150), env)          # ft site 150 > outline 100
    txt = "\n".join(out)
    assert "outside the event" in txt and "bound plan" in txt and "route goal refused for: signed" in txt and "FT-SITE-LEGAL" in txt


def test_blocking_only_with_opt_in():
    assert LG.blocking({}) is False and LG.blocking({"OT_LAUNCH_GATES_BLOCK": "1"}) is True
