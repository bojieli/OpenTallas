"""Loaded-valid qualification (LEC-FPREG-5 10-27, L3 ot_s81_su_rw k / off): an RTL register with no reset that is
only ever loaded with one constant (k <= k_i == K on the first operand row) holds X until that load; synthesis folds
it to the constant.  A hint ['gold', key, ['loaded', c, guard]] binds it to (guard ? c : its free power-up value),
never to c unconditionally.  Proved with the other hypotheses (guard' -> D == c, not X); base case: the guard is
definitely false in the reset state.  Mutants: wrong constant, observed outside the guard, guard true at reset,
a non-constant load, and FSM cube / constraint hints that are wrong.
    python3 -m pytest -q tools/die_plan/test_lec_loaded_valid.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402

IN = ["rn", "ld", "a"]
HINT = ["gold", "ff:u_dut.k", ["loaded", 1, [[["ff:u_dut.v", 1]]]]]


def _mux(m, s, a, b):                     # s ? a : b
    return m.AND(m.AND(s, a) ^ 1, m.AND(s ^ 1, b) ^ 1) ^ 1


def _design(tmp_path, gated=True, load="const"):
    """gold: v resets to 0 and is set on ld (the valid flag); k has no reset, k <= ld ? 1 : k (X until loaded);
    o <= v & a & k (gated) or a & k (MUTANT: k observed before its load).  load 'data' (MUTANT): k <= ld ? a : k.
    gate: synthesis folded k to 1: o <= v & a (gated) or a."""
    def gold(m, l):
        v = m.AND(l["rn"], m.AND(l["v"] ^ 1, l["ld"] ^ 1) ^ 1)
        k = _mux(m, l["ld"], 1 if load == "const" else l["a"], l["k"])
        o = m.AND(l["a"], l["k"])
        return {"v": v, "k": k, "o": m.AND(l["v"], o) if gated else o}

    def gate(m, l):
        v = m.AND(l["rn"], m.AND(l["v"] ^ 1, l["ld"] ^ 1) ^ 1)
        return {"v": v, "o": m.AND(l["v"], l["a"]) if gated else l["a"]}
    g, gm = _seq(tmp_path, "gold", IN, ["v", "k", "o"], gold)
    t, tm = _seq(tmp_path, "gate", IN, ["v", "o"], gate)
    return lec.Lec(g, gm, t, tm)


def _run(tmp_path, monkeypatch, L, hints):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    rec = lec.apply_hints(L, hints, tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    return rec, _sim_prove(m)


def test_unhinted_folded_register_is_not_proved(tmp_path, monkeypatch):
    L = _design(tmp_path)
    _, st = _run(tmp_path, monkeypatch, L, [])
    assert st["ff:u_dut.o"] == "differs"


def test_loaded_register_under_its_valid_flag_is_proved(tmp_path, monkeypatch):
    L = _design(tmp_path)
    rec, st = _run(tmp_path, monkeypatch, L, [HINT])
    assert st["ff:u_dut.o"] == "proved" and st["hyp:gold:ff:u_dut.k"] == "proved"
    assert rec["loaded"] == [dict(register="ff:u_dut.k", value=1, guard=[[["ff:u_dut.v", 1]]], base="reset")]


def test_mutant_wrong_constant_is_dropped(tmp_path, monkeypatch):
    L = _design(tmp_path)
    rec, st = _run(tmp_path, monkeypatch, L, [["gold", "ff:u_dut.k", ["loaded", 0, [[["ff:u_dut.v", 1]]]]]])
    assert ("gold", "ff:u_dut.k") not in L.hyp and "ff:u_dut.k" in rec["dropped"]
    assert st["ff:u_dut.o"] == "differs"


def test_mutant_observed_before_load_differs(tmp_path, monkeypatch):
    L = _design(tmp_path, gated=False)
    _, st = _run(tmp_path, monkeypatch, L, [HINT])
    assert st["ff:u_dut.o"] == "differs"           # the free power-up value reaches o where v == 0


def test_mutant_guard_true_at_reset_is_refused(tmp_path, monkeypatch):
    L = _design(tmp_path)
    rec, st = _run(tmp_path, monkeypatch, L, [["gold", "ff:u_dut.k", ["loaded", 1, [[["ff:u_dut.v", 0]]]]]])
    assert rec["loaded_refused"] and rec["loaded_refused"][0]["register"] == "ff:u_dut.k"
    assert ("gold", "ff:u_dut.k") not in L.hyp and st["ff:u_dut.o"] == "differs"


def test_mutant_data_load_is_dropped(tmp_path, monkeypatch):
    L = _design(tmp_path, load="data")
    rec, st = _run(tmp_path, monkeypatch, L, [HINT])
    assert ("gold", "ff:u_dut.k") not in L.hyp and st["ff:u_dut.o"] == "differs"


def test_malformed_and_matched_targets_are_skipped(tmp_path, monkeypatch):
    L = _design(tmp_path)
    bad = [["gold", "ff:u_dut.v", ["loaded", 1, [[["ff:u_dut.v", 1]]]]],      # matched, not a folded register
           ["gold", "ff:u_dut.k", ["loaded", 2, [[["ff:u_dut.v", 1]]]]],      # not a bit value
           ["gold", "ff:u_dut.k", ["loaded", 1, []]],                           # no guard
           ["gold", "ff:u_dut.k", ["loaded", 1, [[["ff:u_dut.k", 1]]]]],      # guard reads a loaded register
           ["cons", "gate", ["ff:u_dut.v"], [[0]]]]
    rec, st = _run(tmp_path, monkeypatch, L, bad)
    assert len(rec["skipped"]) == 5 and not any(h[0] == "loaded" for h in L.hyp.values())


def test_fsm_cube_and_constraint_hints(tmp_path, monkeypatch):
    """gold 2-bit counter 0..3 (reset 0); gate t1/t2/t3 one-hot for 1/2/3, 0 = no bit.  Correct hints prove; a wrong
    code is dropped; an over-tight constraint (state 3 excluded) fails and takes its cubes with it."""
    def gold(m, l):
        return {"s0": m.AND(l["rn"], l["s0"] ^ 1), "s1": m.AND(l["rn"], m.XOR(l["s0"], l["s1"])),
                "o": m.AND(l["s0"], l["s1"])}

    def gate(m, l):
        zero = m.AND(m.AND(l["t1"] ^ 1, l["t2"] ^ 1), l["t3"] ^ 1)
        return {"t1": m.AND(l["rn"], zero), "t2": m.AND(l["rn"], l["t1"]), "t3": m.AND(l["rn"], l["t2"]),
                "o": l["t3"]}
    g, gm = _seq(tmp_path, "gold", ["rn"], ["s0", "s1", "o"], gold)
    t, tm = _seq(tmp_path, "gate", ["rn"], ["t1", "t2", "t3", "o"], gate)
    S = ["ff:u_dut.s0", "ff:u_dut.s1"]
    cubes = [["gate", f"ff:u_dut.t{c}", ["cube", "gold", S, [c & 1, c >> 1]]] for c in (1, 2, 3)]
    cons = ["cons", "gold", S, [[0, 0], [1, 0], [0, 1], [1, 1]]]
    L = lec.Lec(g, gm, t, tm)
    _, st = _run(tmp_path, monkeypatch, L, cubes + [cons])
    assert st["ff:u_dut.o"] == "proved" and sum(h[0] == "cube" for h in L.hyp.values()) == 3
    L = lec.Lec(g, gm, t, tm)
    wrong = [list(cubes[0]), cubes[1], cubes[2]]
    wrong[0] = ["gate", "ff:u_dut.t1", ["cube", "gold", S, [0, 1]]]
    _, st = _run(tmp_path, monkeypatch, L, wrong + [cons])
    assert ("gate", "ff:u_dut.t1") not in L.hyp
    L = lec.Lec(g, gm, t, tm)
    rec, st = _run(tmp_path, monkeypatch, L, cubes + [["cons", "gold", S, [[0, 0], [1, 0], [0, 1]]]])
    assert not L.cons and not any(h[0] == "cube" for h in L.hyp.values()) and st["ff:u_dut.o"] == "differs"
