"""FLOW-FLEET-R2 C1: one goal table for private-spec, the chain and run_kit.sh's stage resume."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "die_plan"))
import goal_table as GT    # noqa: E402
import kit_wave as KW      # noqa: E402


def test_every_goal_signs_off_or_names_its_stop():
    for g in GT.NAMES:
        assert GT.stop_of(g)
    assert set(GT.SIGNOFF_GOALS) == {"route", "finish"}
    for g in ("cts", "grt", "place", "geom"):
        assert GT.stop_of(g) != "sign-off"


def test_kit_wave_imports_the_table():
    assert KW.PRIVATE_GOALS is GT.NAMES and KW.CHAIN_STAGES is GT.CHAIN_STAGES


def test_every_chain_and_private_goal_is_runnable_on_a_stage_resume():
    for g in GT.CHAIN_STAGES:                            # a goal the chain drives must run on a resumed kit (the 18 SETUP deaths)
        assert GT.resume_goal(g), g
    assert GT.resume_goal("finish") == "route" and GT.resume_goal("synth") == ""
    for g in GT.SIGNOFF_GOALS:
        assert GT.resume_goal(g) in ("route",)


def test_resolve_chain_goal_uses_the_table():
    class AP:
        default_goal = staticmethod(lambda r: "route")
    assert KW.resolve_chain_goal(AP, "auto", {}) == "route" and KW.resolve_chain_goal(AP, "geom", {}) == "route"
    assert KW.resolve_chain_goal(AP, "finish", {"resume": {"start": "cts"}}) == "route" and KW.resolve_chain_goal(AP, "finish", {}) == "finish"
    assert KW.resolve_chain_goal(AP, "grt", {}) == "grt"


def test_run_kit_resume_goals_come_from_the_table():
    import gen_phys
    rk = gen_phys.RUN_KIT
    assert 'case "$GOAL" in ' + "|".join(GT.RESUME_GOALS) + ")" in rk
    for a, b in GT.RESUME_ALIAS.items():
        assert f'[ "$GOAL" = {a} ] && {{ echo "KWRS stage resume: goal {a} runs as {b}' in rk and f"GOAL={b}; }}" in rk


def test_shell_resume_rewrites_from_the_table_and_refuses_a_drifted_script(monkeypatch):
    src = 'x\n  [ "$GOAL" = finish ] && { echo "KWRS stage resume: old"; GOAL=route; }  # KWRS\n  case "$GOAL" in floorplan|place|cts|grt|route) ;; *) echo old; exit 10;; esac  # KWRS\ny\n'
    monkeypatch.setattr(GT, "RESUME_GOALS", ("place", "cts", "grt", "route", "extra"))
    out = GT.shell_resume(src)
    assert "place|cts|grt|route|extra)" in out and "old" not in out.split("case", 1)[1].split("esac")[0].replace("unsupported", "")
    try:
        GT.shell_resume("no goal lines\n")
        assert False
    except ValueError:
        pass
