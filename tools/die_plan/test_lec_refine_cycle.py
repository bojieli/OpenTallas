"""LEC-FPREG-7 10-27 (RXsf, lec-fpreg5/rxsf + lec-fpreg6/rxsf_fill: hyp50..hyp1190 byte-identical miters, 0 failed):
a closure proposal survives the reset-state filter after a fully proved round but is removed again before the next
proof (sim_refine), so the same proved set came back every round until rounds + 1000, where the non-convergence exit
cleared every hypothesis.  A proved set that recurs is a fixpoint: return it (it was proved inductive in full)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _seq, _sim_prove

RS = [f"r[{i}]" for i in range(4)]
K = lambda n: f"ff:u_dut.{n}"


def _design(tmp_path, mutant=False):
    def nxt(gate):
        def make(m, l):
            out = {RS[0]: m.AND(l["rst_n"], l["en"]) if (gate and mutant) else 0, "s": m.AND(l["rst_n"], l["en"])}
            for i in range(1, 4):
                out[RS[i]] = m.AND(l["rst_n"], l[RS[i - 1]])
            return out
        return make
    g, gm = _seq(tmp_path, "gold", ["rst_n", "en"], RS + ["s"], nxt(False))
    t, tm = _seq(tmp_path, "gate", ["rst_n", "en"], RS + ["s"], nxt(True))
    L = lec.Lec(g, gm, t, tm)
    L.hyp = {("both", K(k)): ("const", 0) for k in RS}
    return L


def _run(tmp_path, monkeypatch, mutant=False):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    calls = {"closure": 0}

    def closure(L, log):                    # re-proposes the same non-constant register after every proved round
        calls["closure"] += 1
        L.hyp[("both", K("s"))] = ("const", 0)
        return True

    def sim_drop(L, log, tried, **kw):      # ... which the pre-proof simulation removes again
        return 1 if L.hyp.pop(("both", K("s")), None) else 0
    monkeypatch.setattr(lec, "structural_constant_closure", closure)
    monkeypatch.setattr(lec, "sim_refine", sim_drop)
    monkeypatch.setattr(lec, "noreset_filter", lambda *a, **k: None)
    monkeypatch.setenv("OT_LEC_REFINE_S", "100000")
    for f in ("OT_LEC_COPY_CLOSURE", "OT_LEC_TRACE_CONST"):
        monkeypatch.setenv(f, "0")
    L = _design(tmp_path, mutant)
    log = []
    lec.correspond(L, tmp_path, 100, log, rounds=0)
    return L, log, calls


def test_recurring_proved_set_is_returned_not_cleared(tmp_path, monkeypatch):
    L, log, calls = _run(tmp_path, monkeypatch)
    assert L.hyp == {("both", K(k)): ("const", 0) for k in RS}
    assert calls["closure"] <= 3 and any("fixpoint, returned" in x for x in log)
    assert not any("did not converge" in x for x in log)
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_sim_prove(m).values()) == {"proved"}


def test_recurring_set_mutant_still_differs(tmp_path, monkeypatch):
    # negative control: gate r[0] loads en.  The false constants are dropped by proof first; the fixpoint exit only
    # ever returns a fully proved set, so r[0] still differs.
    L, log, _ = _run(tmp_path, monkeypatch, mutant=True)
    assert ("both", K("r[0]")) not in L.hyp
    m, _ = L.build(with_compare=True, with_hyp=True)
    st = _sim_prove(m)
    assert st[K("r[0]")] == "differs" and all(v == "proved" for n, v in st.items() if n.startswith("hyp:"))
