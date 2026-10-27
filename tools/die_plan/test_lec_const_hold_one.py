"""lec.py: a register that only holds or (re)loads the constant 1 (reset value 1 and every load 1, or no reset and
every load 1) is folded to 1 by synthesis; LEC proposes constant 1 for it (free-at-1 cofactor) and proves it by
induction with the reset input free (LEC-TOOL-1 10-27: HBM argmax_sw_vm_r2 ti[lv][e] low index bits, hcp_sys1
d0 = last ? nlast : 256).  Mutants: a register that resets to 0 or ever loads a non-constant value is refuted.
    python3 -m pytest -q tools/die_plan/test_lec_const_hold_one.py"""
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


IN = ["a", "b", "en", "rst"]


def _gold(kind):
    def f(m, l):
        load = {"x1": 1, "rst1": 1, "rst0": 1, "loadb": l["b"]}[kind]
        c = _mux(m, l["en"], load, l["c1"])
        if kind == "rst1":
            c = _mux(m, l["rst"], 1, c)                  # async reset to 1 (async2sync: rst ? 1 : D)
        if kind == "rst0":
            c = _mux(m, l["rst"], 0, c)                  # MUTANT: resets to 0, loads 1
        return {"c1": c, "r": m.AND(l["a"], l["c1"])}
    return f


def _gate(m, l):                         # synthesis removed c1 as the constant 1: r' = a
    return {"r": l["a"]}


@pytest.mark.parametrize("kind,want", [
    ("x1", "proved"),        # no reset, every load 1 (X power-up): constant 1
    ("rst1", "proved"),      # reset value 1, every load 1: constant 1 from reset
    ("rst0", "differs"),     # MUTANT reset value 0 != load value: not a constant, real difference kept
    ("loadb", "differs"),    # MUTANT loads an input: not a constant
])
def test_constant_one_from_hold(tmp_path, monkeypatch, kind, want):
    monkeypatch.setattr(lec, "prove", _sim_prove)
    g, gm = _seq(tmp_path, "g", IN, ["c1", "r"], _gold(kind))
    t, tm = _seq(tmp_path, "t", IN, ["r"], _gate)
    L = lec.Lec(g, gm, t, tm)
    assert L.gonly == ["ff:u_dut.c1"]
    lec.correspond(L, tmp_path, 100, [])
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert _sim_prove(m)["ff:u_dut.r"] == want
    assert (L.hyp.get(("gold", "ff:u_dut.c1")) == ("const", 1)) == (want == "proved")
