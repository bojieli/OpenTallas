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


def holding(tmp_path, mutant=False, other_state=False):
    regs_g=["ga","o"] + (["gx"] if other_state else [])
    regs_t=["ta","o"] + (["tx"] if other_state else [])
    def ns(m,l,k,extra,inv):
        v=l[extra] if extra in l else l["x"]
        d={k:mux(m,l["en"],v^inv,l[k]),"o":l[k]}
        if extra in l:d[extra]=l["x"]
        return d
    g,gm=_seq(tmp_path,"g",["en","x"],regs_g,lambda m,l:ns(m,l,"ga","gx",0))
    t,tm=_seq(tmp_path,"t",["en","x"],regs_t,lambda m,l:ns(m,l,"ta","tx",int(mutant)))
    return lec.Lec(g,gm,t,tm)


def test_rare_self_holding_alias_has_exact_cofactors(tmp_path):
    L=holding(tmp_path)
    assert lec.self_hold_alias_proposals(L,[]) == 1
    m,_=L.build(with_compare=True,with_hyp=True)
    assert set(_sim_prove(m).values()) == {"proved"}


def test_mutated_load_is_not_a_self_hold_alias(tmp_path):
    L=holding(tmp_path,mutant=True)
    assert lec.self_hold_alias_proposals(L,[]) == 0
    m,_=L.build(with_compare=True,with_hyp=True)
    assert "differs" in _sim_prove(m).values()


def test_other_unpaired_state_is_not_assumed_equal_by_cofactoring(tmp_path):
    assert lec.self_hold_alias_proposals(holding(tmp_path,other_state=True),[]) == 0
