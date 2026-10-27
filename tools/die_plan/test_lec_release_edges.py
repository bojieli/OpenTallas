"""Release-edge constants (LEC-FPREG 10-27): a pipelined fp unit's constant err / exponent bits ride unreset cut
registers (decode constant -> u_k0 .. u_k6, l3 ot_hdc_fp32_mul_f12_l6 u_k6.g_r.r[46] = s2_err[1]) and are constant
only from edge 5, one edge past the default 4-edge reset window.  Synthesis folds them.  The output register that
reads them is held by the core's own synchronous-release reset relay (ot_rst_relay, 2 sync + 1 tree edges after the
port releases), so the X power-up value is never observed: the constant's base case may sit past the window when
release_unmasked shows every reader forced.  Mutants: reader on the raw port (not relay-held), a chain longer than
the relay covers, a primary output reading the register, release edges off.
    python3 -m pytest -q tools/die_plan/test_lec_release_edges.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402


def _mux(m, s, a, b):                     # s ? a : b
    return m.AND(m.AND(s, a) ^ 1, m.AND(s ^ 1, b) ^ 1) ^ 1


IN = ["rn", "a"]


def _design(tmp_path, chain=6, relay=True, hold=False):
    """gold: relay s0 <= rn ? 1 : 0, s1 <= rn ? s0 : 0, r <= rn ? s1 : 0 (ot_rst_relay 2 sync + 1 tree, async
    assert modelled synchronously); k1 <= 0 (a decode constant), k_{i+1} <= k_i, no reset; o <= rst ? a & k_n : 0
    with rst = r (relay) or the raw port rn (MUTANT).  gate: synthesis folded the chain: o <= 0."""
    ks = [f"k{i}" for i in range(1, chain + 1)]

    def gold(m, l):
        nx = {"s0": l["rn"], "s1": m.AND(l["rn"], l["s0"]), "r": m.AND(l["rn"], l["s1"]), "k1": 0}
        for i in range(2, chain + 1):
            nx[f"k{i}"] = l[f"k{i - 1}"]
        rst = l["r"] if relay else l["rn"]
        if hold:      # o has NO reset: it holds unless the relay-held enable writes (NNfd cal_d[slot_f] <= ...)
            nx["o"] = _mux(m, rst, m.AND(l["a"], l[ks[-1]]), l["o"])
        else:
            nx["o"] = m.AND(rst, m.AND(l["a"], l[ks[-1]]))
        return nx
    g, gm = _seq(tmp_path, "gold", IN, ["s0", "s1", "r"] + ks + ["o"], gold)
    if hold:      # gate: the relay and o kept, the write folded (k6 == 0)
        t, tm = _seq(tmp_path, "gate", IN, ["s0", "s1", "r", "o"],
                     lambda m, l: {"s0": l["rn"], "s1": m.AND(l["rn"], l["s0"]), "r": m.AND(l["rn"], l["s1"]),
                                   "o": _mux(m, l["r"] if relay else l["rn"], 0, l["o"])})
    else:
        t, tm = _seq(tmp_path, "gate", IN, ["o"], lambda m, l: {"o": 0})
    return lec.Lec(g, gm, t, tm)


def _verdict(tmp_path, monkeypatch, L):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    log = []
    lec.correspond(L, tmp_path, 100, log)
    m, _ = L.build(with_compare=True, with_hyp=True)
    return _sim_prove(m)["ff:u_dut.o"], log


def test_relay_held_reader_moves_the_base_past_the_window(tmp_path, monkeypatch):
    # k6 constant from edge 6 > 4; o is relay-held through edge 4 + 3 = 7 >= 6
    L = _design(tmp_path)
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "proved" and L.hyp.get(("gold", "ff:u_dut.k6")) == ("const", 0)
    rep = lec.noreset_report(L)
    k6 = [e for e in rep["release"] if e["register"] == "ff:u_dut.k6"]
    assert k6 and k6[0]["edge"] == 6 and rep["n_release"] == 2 and rep["release_edges"] == 8


def test_mutant_reader_on_the_raw_port_is_observable(tmp_path, monkeypatch):
    # o resets from the port itself: after the window the port may release at once, o can load k6's X at edge 5
    L = _design(tmp_path, relay=False)
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "differs" and ("gold", "ff:u_dut.k6") not in L.hyp


def test_mutant_chain_longer_than_the_relay_covers(tmp_path, monkeypatch):
    # k8 constant from edge 8, o relay-held only through edge 7
    L = _design(tmp_path, chain=8)
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "differs" and ("gold", "ff:u_dut.k8") not in L.hyp
    L2 = _design(tmp_path, chain=8)                                   # the base cases themselves:
    L2.hyp = {("gold", f"ff:u_dut.k{i}"): ("const", 0) for i in range(1, 9)}
    ok = lec.noreset_sound(L2)
    assert ("gold", "ff:u_dut.k8") not in ok and ok[("gold", "ff:u_dut.k7")] == 7   # k7: only the free k8 reads it


def test_release_edges_off_restores_the_window_only(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_LEC_RELEASE_EDGES", "0")
    L = _design(tmp_path)
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "differs" and ("gold", "ff:u_dut.k6") not in L.hyp


def test_within_window_chain_unchanged(tmp_path, monkeypatch):
    L = _design(tmp_path, chain=3)
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "proved" and lec.noreset_report(L)["n_release"] == 0


def test_primary_output_reader_blames_the_register():
    # q (var 2) delayed to edge 6, read by output o = q & a; r (var 3) reads q but is forced 0 (and with const 0)
    m = lec.Aig()
    a, q, r = (m.add_input(n) for n in ("a", "q", "r"))
    o = m.AND(q, a)
    z = m.AND(q, 0)
    d = dict(I=1, L=2, A=len(m.ands) // 2, ands=m.ands, latches=[q, z], outputs=[o])

    class _L:
        pass
    L = _L()
    L.gold, L.gp, L._rst_state = d, {"ff:q": q, "ff:r": r}, {"gold": {}}
    L.matched = ["ff:r"]                                                # r is a compare point: must be forced
    assert lec.release_unmasked(L, "gold", {"ff:q": 6}, 4) == {"ff:q"}
    d["outputs"] = []
    L._release_states = {}
    assert lec.release_unmasked(L, "gold", {"ff:q": 6}, 4) == set()     # r = q & 0 is forced: not observed


@pytest.mark.parametrize("relay,want", [(True, "proved"), (False, "differs")])
def test_unreset_reader_with_a_held_write_enable(tmp_path, monkeypatch, relay, want):
    # o itself has no reset (X power-up, a compare point): it is not forced, but its next state does not depend on
    # k6 while the relay holds the write enable low (a forced 0 blocks the taint); the raw-port enable (MUTANT) can
    # write k6's X at edge 5
    L = _design(tmp_path, relay=relay, hold=True)
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == want
