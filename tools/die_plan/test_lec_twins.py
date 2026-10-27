"""lec.py structural / self-holding twins re-added after refinement (BLEC-2 10-26).
    python3 -m pytest -q tools/die_plan/test_lec_twins.py
elemB cerr[11..15]: the merged g_ch[1] valid chain (twins of g_ch[0]) was dropped in a refinement round and never
re-added.  qxpq gbcgr8 (LEC-ICG-2): the self-holding gold-only w_cgt[1] (= qx_gt(oh)[1] = oh[0]) is the merged copy
of w_coh[0]; no exact twin because each next state reads its own register.  Pure python, exact stand-in prover."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec import _aig_bytes, _exact_prove  # noqa: E402

names = lambda ks: {i: [(f"u_dut.{k}$_DFF_P_.lecq", 0)] for i, k in enumerate(ks)}


def _twin_chain(tmp_path, k1_differs):
    """gold-only k0 <= d, k1 <= k0 are twins of the matched c0 <= d, c1 <= c0; matched e reads k1 (gold) / c1
    (gate).  k1_differs: k1 <= k0 & x (negative control).  Inputs d = 2, x = 4; gold c0 6 c1 8 k0 10 k1 12 e 14."""
    g = tmp_path / "gold.aig"
    g.write_bytes(_aig_bytes(2, [2, 6, 2, 16 if k1_differs else 10, 12], [(16, 10, 4)] if k1_differs else []))
    t = tmp_path / "gate.aig"
    t.write_bytes(_aig_bytes(2, [2, 6, 8], []))
    ins = {0: [("d", 0)], 1: [("x", 0)]}
    gm = {"input": ins, "latch": names(["g_ch0.c0", "g_ch0.c1", "g_ch1.k0", "g_ch1.k1", "e"]), "output": {}}
    tm = {"input": ins, "latch": names(["g_ch0.c0", "g_ch0.c1", "e"]), "output": {}}
    return lec.Lec(lec.read_aig(g), gm, lec.read_aig(t), tm)


def _once(name, tag, status="undecided"):
    """exact prover that reports `name` as `status` in proof `tag` only (ABC may leave a deep cone undecided)."""
    def prove(m, work, conflicts, log, tag_=None, **k):
        st = _exact_prove(m)
        if k.get("tag", tag_) == tag and name in st:
            st[name] = status
        return st
    return lambda m, work, conflicts, log, tag="miter", **k: prove(m, work, conflicts, log, tag=tag)


def test_twin_chain_dropped_in_refinement_is_readded(tmp_path, monkeypatch):
    monkeypatch.setattr(lec, "prove", _once("hyp:gold:ff:u_dut.g_ch1.k0", "hyp1"))
    L = _twin_chain(tmp_path, False)
    log = []
    lec.correspond(L, tmp_path, 100, log, rounds=1)
    assert L.hyp.get(("gold", "ff:u_dut.g_ch1.k1"), ("",))[0] == "eq", (L.hyp, log)
    m, _ = L.build(with_compare=True, with_hyp=True)
    res = _exact_prove(m)
    assert set(res.values()) == {"proved"}, res


def test_twin_chain_with_real_difference_still_differs(tmp_path, monkeypatch):
    monkeypatch.setattr(lec, "prove", _once("hyp:gold:ff:u_dut.g_ch1.k0", "hyp1"))
    L = _twin_chain(tmp_path, True)
    lec.correspond(L, tmp_path, 100, [], rounds=1)
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert _exact_prove(m)["ff:u_dut.e"] == "differs"


def _held_twin(tmp_path, data_differs):
    """gbcgr8 shape: c (w_coh[0]) <= en ? x0 : c matched; gold-only k (w_cgt[1]) <= en ? f : k with
    f = x0 | (x0 & y) (== x0, another AIG node); matched o reads k (gold) / c (gate).  data_differs: f = y.
    Inputs en 2, x0 4, y 6; gold latches c 8, k 10, o 12; gate latches c 8, o 10."""
    fl = 7 if data_differs else 23
    g = tmp_path / "gold.aig"
    g.write_bytes(_aig_bytes(3, [19, 29, 10], [(14, 2, 4), (16, 3, 8), (18, 15, 17),          # c'
                                               (20, 4, 6), (22, 5, 21),                       # f = !22
                                               (24, 2, fl ^ 1 if data_differs else fl), (26, 3, 10), (28, 25, 27)]))
    t = tmp_path / "gate.aig"
    t.write_bytes(_aig_bytes(3, [17, 8], [(12, 2, 4), (14, 3, 8), (16, 13, 15)]))
    ins = {0: [("en", 0)], 1: [("x0", 0)], 2: [("y", 0)]}
    gm = {"input": ins, "latch": names(["w_coh0", "w_cgt1", "o"]), "output": {}}
    tm = {"input": ins, "latch": names(["w_coh0", "o"]), "output": {}}
    return lec.Lec(lec.read_aig(g), gm, lec.read_aig(t), tm)


def test_self_holding_merged_twin_is_proposed_and_proved(tmp_path, monkeypatch):
    monkeypatch.setattr(lec, "prove", _exact_prove)
    L = _held_twin(tmp_path, False)
    assert set(L.gonly) == {"ff:u_dut.w_cgt1"}
    log = []
    lec.correspond(L, tmp_path, 100, log)
    assert L.hyp.get(("gold", "ff:u_dut.w_cgt1")) == ("eq", "gold", "ff:u_dut.w_coh0", 0), (L.hyp, log)
    m, _ = L.build(with_compare=True, with_hyp=True)
    res = _exact_prove(m)
    assert set(res.values()) == {"proved"}, res


def test_self_holding_register_with_other_data_still_differs(tmp_path, monkeypatch):
    monkeypatch.setattr(lec, "prove", _exact_prove)
    L = _held_twin(tmp_path, True)
    lec.correspond(L, tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert _exact_prove(m)["ff:u_dut.o"] == "differs"


def test_refuted_twin_is_never_proposed_again(tmp_path, monkeypatch):
    """a closure proposal refuted by a counterexample (injected) stays out: refinement ends, no re-proposal loop."""
    monkeypatch.setattr(lec, "prove", _once("hyp:gold:ff:u_dut.g_ch1.k0", "hyp1", "differs"))
    L = _twin_chain(tmp_path, False)
    log = []
    lec.correspond(L, tmp_path, 100, log, rounds=1)
    assert ("gold", "ff:u_dut.g_ch1.k0", "ff:u_dut.g_ch0.c0", 0) in L.refuted
    assert L.hyp.get(("gold", "ff:u_dut.g_ch1.k0"), ("", "", ""))[2] != "ff:u_dut.g_ch0.c0", (L.hyp, log)
