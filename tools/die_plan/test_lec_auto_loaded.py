"""Auto loaded-valid proposals (KIT-WAVE-16 11-01, LEC NOT EQUIVALENT class): an RTL register with no reset that only
holds itself until it is loaded with one constant (sfu lane g_ld3k p1/p2 <= lane-id bits on ld_e; S81 HEAD
beat_link hold) is X until that load; synthesis folds it, and the no-reset rule (LEC-TOOL-4 10-27) drops its
constant hypothesis.  loaded_proposals finds the reset register whose next state implies the load enable (a
delayed valid ldp_v <= ld_e, or a sticky v <= v | ld) and proposes the approved LEC-FPREG-5 form
['gold', k, ['loaded', c, [[[v, 1]]]]]; apply_hints proves it (guard' -> D == c, guard false in the reset state).
Never X == c: a read outside the guard still differs.  Mutants: observed outside the guard, no guard register,
the LEC-TOOL-4 'hold' register, a data (non-constant) load, auto proposals disabled.
    python3 -m pytest -q tools/die_plan/test_lec_auto_loaded.py"""
import collections

import pytest
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402

IN = ["rn", "ld", "a"]


@pytest.fixture(autouse=True)
def _pre_seq_constant_rule(monkeypatch):
    """these designs are seq constants (COORD 11-05): pin the loaded-hint path under the pre-11-05 rule"""
    monkeypatch.setenv("OT_LEC_SEQ_CONSTANT", "0")


def _mux(m, s, a, b):                     # s ? a : b
    return m.AND(m.AND(s, a) ^ 1, m.AND(s ^ 1, b) ^ 1) ^ 1


def _design(tmp_path, valid="delay", gated=True, load="const"):
    """gold: v resets to 0; valid 'delay': v <= ld (ldp_v <= ld_e), 'sticky': v <= v | ld, 'none' (MUTANT): no v.
    k has no reset, k <= ld ? 1 : k (load 'data' MUTANT: k <= ld ? a : k); o <= v & a & k (gated) or a & k.
    gate: synthesis folded k to 1: o <= v & a (gated) or a."""
    def nv(m, l):
        if valid == "delay":
            return m.AND(l["rn"], l["ld"])
        return m.AND(l["rn"], m.AND(l["v"] ^ 1, l["ld"] ^ 1) ^ 1)

    def gold(m, l):
        nx = {"k": _mux(m, l["ld"], 1 if load == "const" else l["a"], l["k"])}
        o = m.AND(l["a"], l["k"])
        if valid != "none":
            nx["v"] = nv(m, l)
            o = m.AND(l["v"], o) if gated else o
        nx["o"] = o
        return nx

    def gate(m, l):
        if valid == "none":
            return {"o": l["a"]}
        return {"v": nv(m, l), "o": m.AND(l["v"], l["a"]) if gated else l["a"]}
    regs = ["k", "o"] if valid == "none" else ["v", "k", "o"]
    g, gm = _seq(tmp_path, "gold", IN, regs, gold)
    t, tm = _seq(tmp_path, "gate", IN, [r for r in regs if r != "k"], gate)
    return lec.Lec(g, gm, t, tm)


def _flow(tmp_path, monkeypatch, L, auto=True):
    """lec.run's order: correspond -> auto_loaded -> noreset_filter -> compare miter."""
    monkeypatch.setattr(lec, "prove", _sim_prove)
    log, rec = [], {}
    lec.correspond(L, tmp_path, 100, log)
    if auto:
        lec.auto_loaded(L, rec, tmp_path, 100, log)
    lec.noreset_filter(L, log, collections.Counter(), tmp_path, 100)
    m, _ = L.build(with_compare=True, with_hyp=True)
    return rec, _sim_prove(m), log


def test_delayed_valid_load_is_proposed_and_proved(tmp_path, monkeypatch):
    L = _design(tmp_path, "delay")
    rec, st, _ = _flow(tmp_path, monkeypatch, L)
    assert L.hyp.get(("gold", "ff:u_dut.k")) == ("loaded", 1, [[("ff:u_dut.v", 1)]])
    assert rec["auto_loaded"]["proposed"] == 1 and rec["auto_loaded"]["kept"] == 1
    assert st["ff:u_dut.o"] == "proved"


def test_sticky_valid_load_is_proposed_and_proved(tmp_path, monkeypatch):
    L = _design(tmp_path, "sticky")
    rec, st, _ = _flow(tmp_path, monkeypatch, L)
    assert rec["auto_loaded"]["kept"] == 1 and st["ff:u_dut.o"] == "proved"


def test_without_auto_the_folded_register_differs(tmp_path, monkeypatch):
    L = _design(tmp_path, "delay")
    _, st, _ = _flow(tmp_path, monkeypatch, L, auto=False)
    assert st["ff:u_dut.o"] == "differs" and ("gold", "ff:u_dut.k") in L.noreset_dropped


def test_mutant_observed_outside_guard_differs(tmp_path, monkeypatch):
    for valid in ("delay", "sticky"):
        L = _design(tmp_path, valid, gated=False)
        _, st, _ = _flow(tmp_path, monkeypatch, L)
        assert st["ff:u_dut.o"] == "differs"      # the free power-up value reaches o where v == 0


def test_mutant_no_guard_register_gets_no_proposal(tmp_path, monkeypatch):
    L = _design(tmp_path, "none")
    rec, st, _ = _flow(tmp_path, monkeypatch, L)
    assert rec["auto_loaded"]["proposed"] == 0 and st["ff:u_dut.o"] == "differs"


def test_mutant_data_load_is_not_proved(tmp_path, monkeypatch):
    L = _design(tmp_path, "delay", load="data")
    _, st, _ = _flow(tmp_path, monkeypatch, L)
    assert not any(h[0] == "loaded" for h in L.hyp.values()) and st["ff:u_dut.o"] == "differs"


def test_mutant_noreset_hold_register_still_differs(tmp_path, monkeypatch):
    """LEC-TOOL-4 'hold' mutant (k1 <= en ? 0 : k1, observed, no valid flag) stays NOT EQUIVALENT."""
    def gold(m, l):
        z = _mux(m, l["rn"], _mux(m, l["ld"], 0, l["z"]), 0)
        return {"z": z, "k1": _mux(m, l["ld"], 0, l["k1"]), "o": m.AND(l["a"], l["k1"])}
    g, gm = _seq(tmp_path, "gold", IN, ["z", "k1", "o"], gold)
    t, tm = _seq(tmp_path, "gate", IN, ["o"], lambda m, l: {"o": 0})
    L = lec.Lec(g, gm, t, tm)
    rec, st, _ = _flow(tmp_path, monkeypatch, L)
    assert st["ff:u_dut.o"] == "differs" and not any(h[0] == "loaded" for h in L.hyp.values())


def _async_reset_aig(sticky=False, reset_val=0):
    """The AIG shape of an async-reset guard after async2sync + aigmap (HBM g_ld3k ldp_v): the AND with constant 0 is
    kept.  Inputs rn=1 ld=2; latches v=3 k=4.  k has no reset, k <= ld ? 0 : k; v <= rn ? (ld or v | ld) : reset_val."""
    I, Lc = 2, 2
    rn, ld, v, k = 2, 4, 6, 8
    ands = []

    def AND(a, b):
        ands.extend((a, b))
        return 2 * (I + Lc + len(ands) // 2)
    live = (AND(v ^ 1, ld ^ 1) ^ 1) if sticky else ld
    dv = AND(AND(live, rn) ^ 1, AND(rn ^ 1, reset_val) ^ 1) ^ 1
    dk = AND(AND(ld, 0) ^ 1, AND(ld ^ 1, k) ^ 1) ^ 1
    return dict(I=I, L=Lc, O=0, A=len(ands) // 2, latches=[dv, dk], outputs=[], ands=ands), v, k, dv, dk


class _L:
    def __init__(self, d, v, k, dv, dk, reset_val=0):
        self.gold, self.gonly = d, ["ff:k"]
        self.gp, self.gc = {"ff:v": v, "ff:k": k}, {"ff:v": dv, "ff:k": dk}
        self.rst_val = {("gold", "ff:v"): (reset_val, 1)}
        self.noreset_dropped = {("gold", "ff:k"): 0}


def test_async_reset_guard_behind_constant_mux_arm_is_proposed():
    for sticky in (False, True):
        log = []
        assert lec.loaded_proposals(_L(*_async_reset_aig(sticky)), log) == \
            [["gold", "ff:k", ["loaded", 0, [[["ff:v", 1]]]]]], log


def test_valid_with_clear_term_guards_the_load():
    """wq_pv form: v <= (v & ~clr) | (ld & a); k <= (ld & a) ? 0 : k.  Inputs rn=1 ld=2 clr=3 a=4; latches v=5 k=6."""
    I, Lc, ands = 4, 2, []
    rn, ld, clr, a, v, k = 2, 4, 6, 8, 10, 12

    def AND(x, y):
        ands.extend((x, y))
        return 2 * (I + Lc + len(ands) // 2)
    en = AND(ld, a)
    live = AND(AND(v, clr ^ 1) ^ 1, en ^ 1) ^ 1
    dv = AND(AND(live, rn) ^ 1, AND(rn ^ 1, 0) ^ 1) ^ 1
    dk = AND(AND(en, 0) ^ 1, AND(en ^ 1, k) ^ 1) ^ 1
    d = dict(I=I, L=Lc, O=0, A=len(ands) // 2, latches=[dv, dk], outputs=[], ands=ands)
    assert lec.loaded_proposals(_L(d, v, k, dv, dk), []) == [["gold", "ff:k", ["loaded", 0, [[["ff:v", 1]]]]]]


def test_delayed_guard_read_through_async_reset_mux_is_proposed():
    """g_ld3k q2 form: e = rn ? lp : 0; lq <= rn ? e : 0; k <= e ? p : k.  The load enable is the live term of e, one
    level below the leaf of D(lq).  Inputs rn=1; latches lq=2 k=3 lp=4 p=5."""
    I, Lc, ands = 1, 4, []
    rn, lq, k, lp, p = 2, 4, 6, 8, 10

    def AND(x, y):
        ands.extend((x, y))
        return 2 * (I + Lc + len(ands) // 2)
    e = AND(AND(lp, rn) ^ 1, AND(rn ^ 1, 0) ^ 1) ^ 1
    dq = AND(AND(e, rn) ^ 1, AND(rn ^ 1, 0) ^ 1) ^ 1
    dk = AND(AND(e, p) ^ 1, AND(e ^ 1, k) ^ 1) ^ 1
    d = dict(I=I, L=Lc, O=0, A=len(ands) // 2, latches=[dq, dk, lp, p], outputs=[], ands=ands)
    assert lec.loaded_proposals(_L(d, lq, k, dq, dk), []) == [["gold", "ff:k", ["loaded", 0, [[["ff:v", 1]]]]]]


def test_live_term_keeps_two_live_or_terms():
    d, _, _, dv, _ = _async_reset_aig(reset_val=1)     # rn ? ld : 1 has two live terms: no single load condition
    assert lec._live_term(d, dv) == dv


def test_run_calls_auto_loaded_with_opt_out():
    src = Path(lec.__file__).read_text()
    i = src.index('if os.environ.get("OT_LEC_AUTO_LOADED", "1") != "0":')
    assert src.index("auto_loaded(L, rec, out, conflicts, log)", i) < src.index("noreset_filter(L, log", i)
