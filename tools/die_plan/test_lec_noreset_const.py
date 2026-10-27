"""No-reset constants (LEC-TOOL-4 10-27, COORD ruling): a constant hypothesis is kept only when the reset state
gives that constant (the register resets to it, or is reloaded every cycle from registers that do, within
OT_LEC_RESET_CYCLES edges); a register with no reset that only holds itself until its first load is X before that
load and is never assumed constant (HBM hcp_sys1 db <= nf_r on rs_take; argmax ti).  Mutants: such a register
observed before its load, a reload chain longer than the reset window, a register that resets to the other value.
    python3 -m pytest -q tools/die_plan/test_lec_noreset_const.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402
from test_lec_memory_layout import _seq, _sim_prove  # noqa: E402


def _mux(m, s, a, b):                     # s ? a : b
    return m.AND(m.AND(s, a) ^ 1, m.AND(s ^ 1, b) ^ 1) ^ 1


IN = ["rn", "en", "a"]


def _design(tmp_path, kind, chain=1, observed=True):
    """gold: z resets to 0 (rn low) and loads 0 on en (a reset constant); k1..kn no reset; o <= a & k_n (when
    observed).  kind 'reload': k1 <= z every cycle, k_{i+1} <= k_i.  kind 'hold' (MUTANT): k1 <= en ? 0 : k1, no
    reset (X until its first load).  kind 'rst1' (MUTANT): z resets to 1, loads 0 -> not a constant.
    gate: synthesis folded everything: o <= 0."""
    ks = [f"k{i}" for i in range(1, chain + 1)]

    def gold(m, l):
        zr = 1 if kind == "rst1" else 0
        z = _mux(m, l["rn"], _mux(m, l["en"], 0, l["z"]), zr)
        nx = {"z": z}
        nx["k1"] = _mux(m, l["en"], 0, l["k1"]) if kind == "hold" else l["z"]
        for i in range(2, chain + 1):
            nx[f"k{i}"] = l[f"k{i - 1}"]
        nx["o"] = m.AND(l["a"], l[ks[-1]]) if observed else 0
        return nx
    g, gm = _seq(tmp_path, "gold", IN, ["z"] + ks + ["o"], gold)
    t, tm = _seq(tmp_path, "gate", IN, ["o"], lambda m, l: {"o": 0})
    return lec.Lec(g, gm, t, tm)


def _verdict(tmp_path, monkeypatch, L):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    log = []
    lec.correspond(L, tmp_path, 100, log)
    m, _ = L.build(with_compare=True, with_hyp=True)
    return _sim_prove(m)["ff:u_dut.o"], log


def test_reset_port_detection():
    assert all(lec.RESET_PORT.match(n) for n in ("rn", "rst_n", "core_rst_n", "rst", "reset", "rst_ni"))
    assert not any(lec.RESET_PORT.match(n) for n in ("en", "a", "first", "burst_len", "rnd"))


def test_reloaded_from_a_reset_register_is_proved(tmp_path, monkeypatch):
    L = _design(tmp_path, "reload")
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "proved" and L.hyp.get(("gold", "ff:u_dut.k1")) == ("const", 0)
    rep = lec.noreset_report(L)
    k1 = [e for e in rep["reloaded"] if e["register"] == "ff:u_dut.k1"]
    assert rep["enabled"] and k1 and k1[0]["edge"] == 2 and rep["reset_ports"]["gold"] == ["pi:rn[0]"]


def test_mutant_hold_register_observed_before_its_load_fails(tmp_path, monkeypatch):
    L = _design(tmp_path, "hold")
    st, log = _verdict(tmp_path, monkeypatch, L)
    assert st == "differs" and ("gold", "ff:u_dut.k1") not in L.hyp
    assert ("gold", "ff:u_dut.k1") in L.noreset_dropped and any("no-reset constants" in x for x in log)
    assert {"register": "ff:u_dut.k1", "side": "gold", "value": 0} in lec.noreset_report(L)["dropped"]


def test_unobserved_hold_register_needs_no_constant(tmp_path, monkeypatch):
    L = _design(tmp_path, "hold", observed=False)
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "proved" and ("gold", "ff:u_dut.k1") not in L.hyp


def test_opt_out_restores_the_x_power_up_constant(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_LEC_NORESET_CONST", "0")
    L = _design(tmp_path, "hold")
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "proved" and L.hyp.get(("gold", "ff:u_dut.k1")) == ("const", 0)
    assert lec.noreset_report(L)["enabled"] is False


@pytest.mark.parametrize("cycles,want", [("4", "proved"), ("2", "differs")])
def test_mutant_reload_chain_longer_than_the_reset_window(tmp_path, monkeypatch, cycles, want):
    # z (edge 1) -> k1 (2) -> k2 (3): constant only from edge 3
    monkeypatch.setenv("OT_LEC_RESET_CYCLES", cycles)
    st, _ = _verdict(tmp_path, monkeypatch, _design(tmp_path, "reload", chain=2))
    assert st == want


def test_mutant_reset_to_the_other_value_is_not_a_constant(tmp_path, monkeypatch):
    L = _design(tmp_path, "rst1")
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "differs" and ("gold", "ff:u_dut.k1") not in L.hyp


def test_reset_state_is_constant_propagation_only():
    # z: rn ? z : 0 (reset 0, holds); h: no reset, holds; c: reloads ~z every cycle
    m = lec.Aig()
    rn, z, h, c = (m.add_input(n) for n in ("rn", "z", "h", "c"))
    d = dict(I=1, L=3, A=0, ands=None, latches=None)
    nz = m.AND(rn, z)
    d.update(A=len(m.ands) // 2, ands=m.ands, latches=[nz, h, z ^ 1])
    st, first = lec.reset_state(d, {1: 0}, 3)
    assert st == {2: 0, 4: 1} and first == {2: 1, 4: 2}           # h (var 3) stays unknown


def test_rejected_closure_constant_does_not_restart_proved_rounds(tmp_path, monkeypatch):
    L = _design(tmp_path, "hold")
    proposed = ("gold", "ff:u_dut.k1")
    calls = []
    original = lec.structural_constant_closure

    def closure(L, log):
        n = original(L, log)
        L.hyp[proposed] = ("const", 0)
        calls.append(1)
        return n + 1

    monkeypatch.setattr(lec, "structural_constant_closure", closure)
    st, log = _verdict(tmp_path, monkeypatch, L)
    assert st == "differs"                 # the invalid no-reset constant stays rejected
    assert proposed not in L.hyp
    assert L.hyp[("gold", "ff:u_dut.z")] == ("const", 0)  # valid proof survives
    assert len(calls) < 5
    assert not any("did not converge" in x for x in log)


def test_reset_pin_suffix_is_detected_with_stem_polarity():
    # The standard physical core pin is rst_n_pin. The final n of the word
    # "pin" must not turn an active-high reset_pin into an active-low reset.
    p = {"pi:rst_n_pin[0]": 2, "pi:reset_pin[0]": 4, "pi:burst_len_pin[0]": 6}
    assert lec.reset_vars({}, p) == {1: 0, 2: 1}


def test_pin_reset_loads_gated_unreset_constant_before_release(tmp_path, monkeypatch):
    # BF tile clock: its enable resets to one; the enabled data capture
    # p<=1 has no reset of its own. Under reset it loads at edge 2.
    # Thereafter p==1 is inductive even when the clock enable goes low.
    inputs = ["rst_n_pin", "en"]
    def gold(m, l):
        return {"ze": _mux(m, l["rst_n_pin"], l["en"], 1),
                "p": _mux(m, l["ze"], 1, l["p"]), "o": l["p"]}
    g, gm = _seq(tmp_path, "gold", inputs, ["ze", "p", "o"], gold)
    t, tm = _seq(tmp_path, "gate", inputs, ["ze", "o"],
                 lambda m, l: {"ze": _mux(m, l["rst_n_pin"], l["en"], 1), "o": 1})
    L = lec.Lec(g, gm, t, tm)
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "proved"
    assert L.hyp[("gold", "ff:u_dut.p")] == ("const", 1)
    assert L.rst_val[("gold", "ff:u_dut.p")] == (1, 2)


def test_pin_reset_wrong_enable_polarity_keeps_difference(tmp_path, monkeypatch):
    inputs = ["rst_n_pin", "en"]
    g, gm = _seq(tmp_path, "gold", inputs, ["ze", "p", "o"], lambda m, l: {
        # MUTANT: enable resets to zero, so p is still unknown throughout reset.
        "ze": _mux(m, l["rst_n_pin"], l["en"], 0),
        "p": _mux(m, l["ze"], 1, l["p"]), "o": l["p"]})
    t, tm = _seq(tmp_path, "gate", inputs, ["ze", "o"],
                 lambda m, l: {"ze": _mux(m, l["rst_n_pin"], l["en"], 0), "o": 1})
    L = lec.Lec(g, gm, t, tm)
    st, _ = _verdict(tmp_path, monkeypatch, L)
    assert st == "differs" and ("gold", "ff:u_dut.p") not in L.hyp
