"""LEC-FPREG-3 10-27 (SYS_C 4,561 differ): an expired refinement budget finishes monotonically instead of clearing
every hypothesis.  A false constant chain that peels one bit per round must not wipe unrelated true constants."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _seq, _sim_prove

N = 60          # longer than rounds + 40: the budget expires while the false chain still peels


def _design(tmp_path, mutant=False):
    qs = [f'q[{i}]' for i in range(N)]
    rs = [f'r[{i}]' for i in range(4)]

    def nxt(gate):
        def make(m, l):
            out = {qs[0]: m.AND(l['rst_n'], l['en'])}
            for i in range(1, N):
                out[qs[i]] = m.AND(l['rst_n'], l[qs[i - 1]])
            # r: true constant-0 chain (gold); the mutant gate loads en into r[0] (r is NOT constant there)
            out[rs[0]] = m.AND(l['rst_n'], l['en']) if (gate and mutant) else 0
            for i in range(1, 4):
                out[rs[i]] = m.AND(l['rst_n'], l[rs[i - 1]])
            return out
        return make

    g, gm = _seq(tmp_path, 'gold', ['rst_n', 'en'], qs + rs, nxt(False))
    t, tm = _seq(tmp_path, 'gate', ['rst_n', 'en'], qs + rs, nxt(True))
    L = lec.Lec(g, gm, t, tm)
    L.hyp = {('both', f'ff:u_dut.{k}'): ('const', 0) for k in qs + rs}
    return L


def _run(tmp_path, monkeypatch, monotone, mutant=False):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    # SAT-only refutation, as in SYS_C (the rare counter carries survived the concrete simulation lanes): the
    # simulation pre-filter is bypassed so the false chain peels one register per proof round
    monkeypatch.setattr(lec, "sim_refine", lambda *a, **k: 0)
    monkeypatch.setenv("OT_LEC_REFINE_S", "0")
    monkeypatch.setenv("OT_LEC_REFINE_MONOTONE", "1" if monotone else "0")
    for f in ("OT_LEC_COPY_CLOSURE", "OT_LEC_TRACE_CONST"):
        monkeypatch.setenv(f, "0")
    L = _design(tmp_path, mutant)
    log = []
    lec.correspond(L, tmp_path, 100, log, rounds=0)
    return L, log


def test_old_clear_all_loses_true_constants(tmp_path, monkeypatch):
    L, log = _run(tmp_path, monkeypatch, monotone=False)
    assert L.hyp == {}
    assert any("did not converge" in x for x in log)


def test_monotone_finish_keeps_true_constants_and_is_inductive(tmp_path, monkeypatch):
    L, log = _run(tmp_path, monkeypatch, monotone=True)
    assert L.hyp == {('both', f'ff:u_dut.r[{i}]'): ('const', 0) for i in range(4)}
    assert any("monotone finish" in x for x in log)
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_sim_prove(m).values()) == {'proved'}


def test_monotone_finish_mutant_still_differs(tmp_path, monkeypatch):
    # negative control: gate r[0] loads en.  r[0] and its fanout lose their constants (dropped, never kept), and the
    # compare point r[0] differs; the finish removes assumptions only, it never hides a difference.
    L, _ = _run(tmp_path, monkeypatch, monotone=True, mutant=True)
    assert ('both', 'ff:u_dut.r[0]') not in L.hyp
    m, _ = L.build(with_compare=True, with_hyp=True)
    st = _sim_prove(m)
    assert st['ff:u_dut.r[0]'] == 'differs'
    assert all(v == 'proved' for n, v in st.items() if n.startswith('hyp:'))


def test_cascade_drop_is_transitive_and_local():
    class Fake:
        pass
    L = Fake()
    L.hyp = {('gold', 'a'): ('const', 0), ('gold', 'b'): ('const', 0), ('gold', 'c'): ('const', 1),
             ('gate', 'd'): ('eq', 'gold', 'x', 0)}
    sup = {('gold', 'a'): {'z'}, ('gold', 'b'): {'a'}, ('gold', 'c'): {'y'}, ('gate', 'd'): {'b', 'e'}}
    out = lec.cascade_drop(L, sup, {'z'})
    assert set(out) == {('gold', 'a'), ('gold', 'b'), ('gate', 'd')}
    assert L.hyp == {('gold', 'c'): ('const', 1)}
