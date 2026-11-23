"""FLOW-FLEET-R2: a pinned --stage request that never started is widened to a spill list after PIN_SPILL_AFTER_S."""
import importlib.machinery, importlib.util, pathlib
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_pinspill", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_pinspill", l)); l.exec_module(RUN)
FLEET = ["epyc7", "epyc8", "epyc9", "epyc10", "intel1"]
BASE = ["--mem", "48", "--threads", "16", "--dir", "/srv/k", "--stage", "/srv/k", "--hosts", "epyc9", "--", "bash", "x"]
LATE = RUN.PIN_SPILL_AFTER_S + 1


def hv(a):
    return a[a.index("--hosts") + 1]


def test_widened_after_the_wait_with_the_pin_first():
    a = RUN.pin_spill_args(BASE, LATE, FLEET, env={})
    assert hv(a) == "epyc9,epyc7,epyc8,epyc10,intel1" and a[a.index("--"):] == ["--", "bash", "x"] and hv(BASE) == "epyc9"   # input not mutated


def test_not_before_the_wait():
    assert RUN.pin_spill_args(BASE, RUN.PIN_SPILL_AFTER_S - 1, FLEET, env={}) is BASE


def test_keeps_the_pin_for_opt_outs_and_other_shapes():
    for env in ({"OT_RUN_STRICT_HOST": "1"}, {"OT_RUN_NO_PIN_SPILL": "1"}, {"OT_RUN_NO_SPILL": "1"}):
        assert RUN.pin_spill_args(BASE, LATE, FLEET, env=env) is BASE
    strict = BASE[:-3] + ["--strict-host"] + BASE[-3:]
    assert RUN.pin_spill_args(strict, LATE, FLEET, env={}) is strict
    nostage = ["--mem", "48", "--hosts", "epyc9", "--dir", "/srv/k", "--", "bash", "x"]
    assert RUN.pin_spill_args(nostage, LATE, FLEET, env={}) is nostage                       # no --stage: its inputs are not declared
    sealed = BASE[:-3] + ["--job", "/x.json"] + BASE[-3:]
    assert RUN.pin_spill_args(sealed, LATE, FLEET, env={}) is sealed                         # sealed jobs re-hand through ot-run-sealed
    multi = ["--hosts", "epyc9,epyc8", "--stage", "/k", "--", "x"]
    assert RUN.pin_spill_args(multi, LATE, FLEET, env={}) is multi                           # already a list
    assert RUN.pin_spill_args(BASE, LATE, ["epyc9"], env={}) is BASE                         # nothing to widen to


def test_a_stage_flag_after_the_command_does_not_count():
    a = ["--mem", "8", "--hosts", "epyc9", "--", "tool", "--stage", "x"]
    assert RUN.pin_spill_args(a, LATE, FLEET, env={}) is a
