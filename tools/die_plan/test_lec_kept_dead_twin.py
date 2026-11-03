"""S81 ve_s 11-03: routed LEC proved 43609/43609 but KEEP FAIL 447 kept bits: twin registers synthesis merged
(gold u_exp3[i] proved == u_exp2[i]) and eliminate_dead_logic then removed with the surviving twin.  A class of
kept bits is exempt only when every member is missing, all relations are gold-gold eq among the members, nothing
else reads them and the representative is free (the caller requires every compare point proved).  Mutants: a
surviving twin, a gate/both pairing, a constant, a cube/cons reader, two free roots.
python3 -m pytest -q tools/die_plan/test_lec_kept_dead_twin.py"""
from types import SimpleNamespace

import lec

A, B, C = "ff:u_dut.t0.u_exp2[0]", "ff:u_dut.t0.u_exp3[0]", "ff:u_dut.t0.u_exp4[0]"


def _L(hyp, cons=()):
    return SimpleNamespace(hyp=hyp, cons=list(cons))


def test_dead_twin_class_exempt():
    L = _L({("gold", B): ("eq", "gold", A, 0), ("gold", C): ("eq", "gold", B, 1)})
    assert lec.kept_dead_twin_classes(L, [A, B, C]) == {A, B, C}
    # the single-bit rule alone does not rescue it (both are named by a hypothesis)
    assert lec.kept_functionally_unobservable(L, [A, B, C], True) == []


def test_surviving_twin_stays_missing():
    # mutant: the representative A is still a flop in the gate (not in the missing list) -> a real merge
    L = _L({("gold", B): ("eq", "gold", A, 0)})
    assert lec.kept_dead_twin_classes(L, [B]) == set()


def test_gate_or_both_pairing_stays_missing():
    L = _L({("gold", B): ("eq", "gold", A, 0), ("gate", "ff:u_dut.g"): ("eq", "gold", A, 0)})
    assert lec.kept_dead_twin_classes(L, [A, B]) == set()
    L = _L({("gold", B): ("eq", "gold", A, 0), ("both", "ff:u_dut.m"): ("eq", "gold", B, 0)})
    assert lec.kept_dead_twin_classes(L, [A, B]) == set()


def test_constant_or_reader_stays_missing():
    L = _L({("gold", B): ("eq", "gold", A, 0), ("gold", A): ("const", 0)})
    assert lec.kept_dead_twin_classes(L, [A, B]) == set()
    L = _L({("gold", B): ("eq", "gold", A, 0), ("gate", "ff:u_dut.q"): ("cube", "gold", [A, "ff:u_dut.x"], [1, 0])})
    assert lec.kept_dead_twin_classes(L, [A, B]) == set()
    L = _L({("gold", B): ("eq", "gold", A, 0)}, cons=[("gold", [B], [[0]])])
    assert lec.kept_dead_twin_classes(L, [A, B]) == set()


def test_unrelated_missing_bits_untouched():
    L = _L({("gold", B): ("eq", "gold", A, 0)})
    assert lec.kept_dead_twin_classes(L, [A, B, "ff:u_dut.free"]) == {A, B}
