"""Pipeline fill (LEC-FPREG-6 10-27, RXsf ot_hdc_v41x_exp_s xc5/6/7[31]): an RTL register with no reset on an
every-cycle pipeline whose source is a constant (x = {1'b1, x[30:0]}) holds X until the constant has ridden down to
it; synthesis folds the whole line.  A hint ['gold', key, ['fill', c, pred]] binds it to (filled ? c : X) with a
tool-owned ghost bit (filled' = filled(pred), the root's filled' = 1), never to c unconditionally.  Proved with the
other hypotheses: filled' -> D == c and not X, not filled' -> D is X (tight).  Mutants: a gate bug after the fill,
a data source, the wrong constant, a lagging ghost (pred deeper than the real predecessor), a broken chain and other
hint forms reading a fill register.
    python3 -m pytest -q tools/die_plan/test_lec_pipeline_fill.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402

N = 6                                      # deeper than the 4-edge reset window: p5, p6 are X in the reset state
IN = ["rn", "a"]
P = [f"p{i}" for i in range(1, N + 1)]
Q = [f"q{i}" for i in range(1, N + 1)]
K = lambda n: f"ff:u_dut.{n}"


def chain(names, c=1):
    return [["gold", K(n), ["fill", c, None if i == 0 else K(names[i - 1])]] for i, n in enumerate(names)]


def _design(tmp_path, src="const", gate_bug=False):
    """gold: p1 <= 1 (src 'data' MUTANT: p1 <= a), p[i] <= p[i-1], q likewise (a second folded line), all without
    reset; o <= a ^ p6 (no reset, loaded every cycle: it reads p6 while it is still X).  r resets (the reset port).
    gate: synthesis folded p and q: o <= a ^ 1 (gate_bug MUTANT: o <= a)."""
    def gold(m, l):
        n = {"r": m.AND(l["rn"], l["r"] ^ 1) ^ 1, "p1": 1 if src == "const" else l["a"], "q1": 1}
        for i in range(1, N):
            n[P[i]], n[Q[i]] = l[P[i - 1]], l[Q[i - 1]]
        n["o"] = m.XOR(l["a"], l["p6"])
        return n

    def gate(m, l):
        return {"r": m.AND(l["rn"], l["r"] ^ 1) ^ 1, "o": l["a"] if gate_bug else l["a"] ^ 1}
    g, gm = _seq(tmp_path, "gold", IN, ["r"] + P + Q + ["o"], gold)
    t, tm = _seq(tmp_path, "gate", IN, ["r", "o"], gate)
    return lec.Lec(g, gm, t, tm)


def _run(tmp_path, monkeypatch, L, hints):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    rec = lec.apply_hints(L, hints, tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    return rec, _sim_prove(m)


def test_unhinted_folded_line_is_not_proved(tmp_path, monkeypatch):
    L = _design(tmp_path)
    _, st = _run(tmp_path, monkeypatch, L, [])
    assert st[K("o")] == "differs"


def test_filled_line_is_proved_and_reported(tmp_path, monkeypatch):
    L = _design(tmp_path)
    rec, st = _run(tmp_path, monkeypatch, L, chain(P))
    assert st[K("o")] == "proved" and all(st[f"hyp:gold:{K(n)}"] == "proved" for n in P)
    assert [f["register"] for f in rec["fill"]] == [K(n) for n in P] and not rec["dropped"]
    assert lec.fill_live(L.hyp) == {K(n) for n in P}


def test_mutant_gate_bug_after_fill_differs(tmp_path, monkeypatch):
    L = _design(tmp_path, gate_bug=True)
    _, st = _run(tmp_path, monkeypatch, L, chain(P))
    assert st[K("o")] == "differs"                 # filled: gold o = a ^ 1, gate o = a


def test_mutant_data_source_is_dropped(tmp_path, monkeypatch):
    L = _design(tmp_path, src="data")
    rec, st = _run(tmp_path, monkeypatch, L, chain(P))
    assert not any(h[0] == "fill" for h in L.hyp.values()) and st[K("o")] == "differs"


def test_mutant_wrong_constant_is_refused_or_dropped(tmp_path, monkeypatch):
    L = _design(tmp_path)
    rec, st = _run(tmp_path, monkeypatch, L, chain(P, c=0))
    assert rec["fill_refused"] and not any(h[0] == "fill" for h in L.hyp.values())
    assert st[K("o")] == "differs"


def test_mutant_lagging_ghost_is_dropped(tmp_path, monkeypatch):
    """p3's ghost taken from q5 (two edges later than its real predecessor p2): the ghost would call p3 X while the
    RTL already holds 1.  The tight obligation (not filled' -> D is X) refutes it."""
    L = _design(tmp_path)
    hints = chain(Q) + [h if h[1] != K("p3") else ["gold", K("p3"), ["fill", 1, K("q5")]] for h in chain(P)]
    rec, st = _run(tmp_path, monkeypatch, L, hints)
    assert ("gold", K("p3")) not in L.hyp and K("p3") in rec["dropped"]


def test_mutant_broken_chain_is_dropped(tmp_path, monkeypatch):
    L = _design(tmp_path)
    rec, st = _run(tmp_path, monkeypatch, L, chain(P)[1:])     # p1 has no hint: p2 names an unhinted predecessor
    assert not any(h[0] == "fill" for h in L.hyp.values()) and st[K("o")] == "differs"


def test_malformed_and_cross_reads_are_skipped(tmp_path, monkeypatch):
    L = _design(tmp_path)
    bad = [["gold", K("o"), ["fill", 1, None]],                   # matched, not a folded register
           ["gold", K("p1"), ["fill", 2, None]],                  # not a bit value
           ["gold", K("p2"), ["fill", 1, K("p2")]],               # its own predecessor
           ["gate", K("p1"), ["fill", 1, None]],                  # gold registers only
           ["gold", K("q2"), ["loaded", 1, [[[K("p1"), 1]]]]],    # another form reading a fill register
           ["cons", "gold", [K("p1")], [[1]]]]
    rec, st = _run(tmp_path, monkeypatch, L, bad)
    assert len(rec["skipped"]) == 6 and not any(h[0] in ("fill", "loaded") for h in L.hyp.values())


def test_fill_mux_bound_after_every_input(tmp_path, monkeypatch):
    """ROOT-MERGE-81b 10-27 regression: the (filled ? c : X) mux was built (ANDs) inside the input loop, so the next
    fill ghost or gold-only register (sorted after it) raised 'inputs after ands'.  Fills on p only: the unhinted q
    registers sort after every p fill and must still become plain inputs, with no AND before the last input."""
    L = _design(tmp_path)
    monkeypatch.setattr(lec, "prove", _sim_prove)
    lec.apply_hints(L, chain(P), tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    names = m.inames
    assert sum(n.startswith("fill:") for n in names) == N
    assert any(n.endswith(K("q6")) for n in names)   # a gold-only register bound after the fills
    assert _sim_prove(m)[K("o")] == "proved"


def test_fill_mux_bound_after_every_input(tmp_path, monkeypatch):
    """ROOT-MERGE-81b 10-27 regression: the (filled ? c : X) mux was built (ANDs) inside the input loop, so the next
    fill ghost or gold-only register (sorted after it) raised 'inputs after ands'.  Fills on p only: the unhinted q
    registers sort after every p fill and must still become plain inputs, with no AND before the last input."""
    L = _design(tmp_path)
    monkeypatch.setattr(lec, "prove", _sim_prove)
    lec.apply_hints(L, chain(P), tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert sum(n.startswith("fill:") for n in m.inames) == N
    assert any(n.endswith(K("q6")) for n in m.inames)   # a gold-only register bound after the fills
    assert _sim_prove(m)[K("o")] == "proved"
