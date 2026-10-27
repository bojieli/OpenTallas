"""lec.py: a gold-only register that is never written (next state == its own Q; slang's padding words of a
non-power-of-two unpacked array) is an X source, not the constant 0 that write_aiger -zinit gives it
(LEC-ICG-2 10-26: qxpq_w10 _gb cfg_d 27 bits NOT EQUIVALENT only at the unreachable rg_s >= 5).
    python3 -m pytest -q tools/die_plan/test_lec_unwritten_x.py"""
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lec  # noqa: E402


def _sim_prove(m, *a, **k):
    val, mask = m.simulate(16, seed=12345)
    return {n: ("proved" if lec.lit_val(val, mask, o) == 0 else "differs") for n, o in zip(m.onames, m.outs)}


def _seq(tmp_path, name, inputs, latches, nxt_fn):
    m = lec.Aig()
    lits = {n: m.add_input(n) for n in list(inputs) + list(latches)}
    nxt = nxt_fn(m, lits)
    f = tmp_path / (name + ".aig")
    m.write(f)
    _, body = f.read_bytes().split(b"\n", 1)
    A = len(m.ands) // 2
    hdr = f"aig {m.ni + A} {len(inputs)} {len(latches)} 0 {A}\n" + "".join(f"{nxt[l]}\n" for l in latches)
    f.write_bytes(hdr.encode() + body)
    mp = {"input": {i: [(n, 0)] for i, n in enumerate(inputs)},
          "latch": {i: [(f"u_dut.{n}$_DFF_P_.lecq", 0)] for i, n in enumerate(latches)}, "output": {}}
    return lec.read_aig(f), mp


def _mux(m, s, a, b):                    # s ? a : b
    return m.AND(m.AND(s, a) ^ 1, m.AND(s ^ 1, b) ^ 1) ^ 1


def _gold(written):
    # sel' = s; pad' = pad (never written) or we ? a : pad; r' = sel ? pad : a  (r = rg_d[rg_s], pad = rg_d[5])
    def f(m, l):
        pad = _mux(m, l["we"], l["a"], l["pad"]) if written else l["pad"]
        return {"sel": l["s"], "pad": pad, "r": _mux(m, l["sel"], l["pad"], l["a"])}
    return f


def _gate(sel_value):
    # read_verilog: r' = sel ? X : a, synthesis chose sel_value for the X (here 1 or !a)
    def f(m, l):
        return {"sel": l["s"], "r": _mux(m, l["sel"], 1 if sel_value == "1" else l["a"] ^ 1, l["a"])}
    return f


@pytest.mark.parametrize("written,sel_value,want", [
    (False, "1", "proved"),          # the padding word is X: any gate value at sel refines it
    (False, "!a", "proved"),
    (True, "1", "differs"),          # a register the RTL writes is a real state: never relaxed to X
])
def test_unwritten_register_is_x(tmp_path, monkeypatch, written, sel_value, want):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    g, gm = _seq(tmp_path, "g", ["a", "s", "we"], ["sel", "pad", "r"], _gold(written))
    t, tm = _seq(tmp_path, "t", ["a", "s", "we"], ["sel", "r"], _gate(sel_value))
    L = lec.Lec(g, gm, t, tm)
    assert L.gonly == ["ff:u_dut.pad"]
    lec.correspond(L, tmp_path, 100, [])
    m, kind = L.build(with_compare=True, with_hyp=True)
    assert L.unwritten == ([] if written else ["ff:u_dut.pad"])
    st = _sim_prove(m)
    assert st["ff:u_dut.r"] == want
    if not written:
        assert ("gold_x", "ff:u_dut.pad") in kind.values()


def test_unwritten_x_does_not_mask_a_real_difference(tmp_path, monkeypatch):
    # gate r' = sel ? 1 : !a differs from gold wherever sel = 0 (gold not X there)
    monkeypatch.setattr(lec, "prove", _sim_prove)
    g, gm = _seq(tmp_path, "g", ["a", "s", "we"], ["sel", "pad", "r"], _gold(False))

    def bad(m, l):
        return {"sel": l["s"], "r": _mux(m, l["sel"], 1, l["a"] ^ 1)}
    t, tm = _seq(tmp_path, "t", ["a", "s", "we"], ["sel", "r"], bad)
    L = lec.Lec(g, gm, t, tm)
    lec.correspond(L, tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert _sim_prove(m)["ff:u_dut.r"] == "differs"

