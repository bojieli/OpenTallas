"""Copy candidates need per-design trace agreement; induction still proves both sides."""
import collections
import lec
from test_lec_memory_layout import _seq, _sim_prove


def design(tmp_path, mutant=False, wrong_design=False):
    g, gm = _seq(tmp_path, "g", ["x", "y"], ["a", "b", "o"],
                 lambda m, l: {"a": l["x"], "b": l["x"], "o": l["a"]})
    t, tm = _seq(tmp_path, "t", ["x", "y"], ["a", "b", "o"],
                 lambda m, l: {"a": l["y"] if wrong_design else l["x"],
                               "b": (l["y"] if wrong_design else l["x"]) ^ int(mutant), "o": l["b"]})
    return lec.Lec(g, gm, t, tm)


def traces():
    # Corresponding copies have not yet gained cross-design trace agreement.
    return {(sd, "ff:u_dut."+k): v for sd,v in (("gold", (11, 22)), ("gate", (33, 44))) for k in ("a", "b")}


def test_valid_copies_proposed_without_cross_design_trace_equality(tmp_path):
    L = design(tmp_path)
    assert lec.matched_copy_closure(L, [], traces(), collections.Counter()) == 1
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert set(_sim_prove(m).values()) == {"proved"}


def test_wrong_copy_is_refuted_even_with_forged_trace(tmp_path):
    L = design(tmp_path, mutant=True)
    assert lec.matched_copy_closure(L, [], traces(), collections.Counter()) == 0
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert "differs" in _sim_prove(m).values()


def test_copy_merges_do_not_hide_cross_design_data_mutation(tmp_path):
    L = design(tmp_path, wrong_design=True)
    assert lec.matched_copy_closure(L, [], traces(), collections.Counter()) == 1
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert "differs" in _sim_prove(m).values()
