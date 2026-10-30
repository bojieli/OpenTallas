"""Rare-command copies and scalar/vector aliases remain proved obligations."""
import collections
import json
import lec
from test_lec_memory_layout import _seq, _sim_prove


def mux(m, s, a, b):
    return m.AND(m.AND(s, a)^1, m.AND(s^1, b)^1)^1


def copies(tmp_path, mutant=False):
    g, gm = _seq(tmp_path, "g", ["en", "x"], ["a", "b", "o"],
        lambda m,l: {"a":mux(m,l["en"],l["x"],l["a"]),
                     "b":mux(m,l["en"],l["x"],l["a"]), "o":l["a"]})
    t, tm = _seq(tmp_path, "t", ["en", "x"], ["a", "b", "o"],
        lambda m,l: {"a":mux(m,l["en"],l["x"],l["a"]),
                     "b":mux(m,l["en"],l["x"]^int(mutant),l["b"]), "o":l["b"]})
    return lec.Lec(g,gm,t,tm)


def test_exact_d_copies_need_no_cross_design_or_nonconstant_trace(tmp_path):
    L=copies(tmp_path)
    assert lec.matched_d_copy_closure(L,[],collections.Counter()) == 1
    m,_=L.build(with_compare=True,with_hyp=True)
    assert set(_sim_prove(m).values()) == {"proved"}


def test_wrong_copy_is_refuted(tmp_path):
    L=copies(tmp_path,True)
    assert lec.matched_d_copy_closure(L,[],collections.Counter()) == 0
    m,_=L.build(with_compare=True,with_hyp=True)
    assert "differs" in _sim_prove(m).values()


def alias(tmp_path, mutant=False, ambiguous=False):
    g,gm=_seq(tmp_path,"g",["x"],["cap[0]","o"],
               lambda m,l:{"cap[0]":l["x"],"o":l["cap[0]"]})
    t,tm=_seq(tmp_path,"t",["x"],["scalar","o"],
               lambda m,l:{"scalar":l["x"]^int(mutant),"o":l["scalar"]})
    L=lec.Lec(g,gm,t,tm)
    nets={"u_dut.cap":{"bits":[42,43]},"u_dut.scalar":{"bits":[42]}}
    if ambiguous:
        nets["u_dut.cap"]={"bits":[44,43]}
    (tmp_path/"gold.aliases.json").write_text(json.dumps({"modules":{"top":{"netnames":nets}}}))
    return L


def test_exact_bit_alias_across_different_vector_widths(tmp_path):
    L=alias(tmp_path)
    assert lec.json_bit_alias_proposals(L,[],tmp_path) == 1
    m,_=L.build(with_compare=True,with_hyp=True)
    assert set(_sim_prove(m).values()) == {"proved"}


def test_wrong_data_is_not_hidden_by_exact_bit_alias_candidate(tmp_path):
    L=alias(tmp_path,True)
    assert lec.json_bit_alias_proposals(L,[],tmp_path) == 1
    m,_=L.build(with_compare=True,with_hyp=True)
    assert "differs" in _sim_prove(m).values()


def test_different_bit_identity_gets_no_proposal(tmp_path):
    assert lec.json_bit_alias_proposals(alias(tmp_path,ambiguous=True),[],tmp_path) == 0
