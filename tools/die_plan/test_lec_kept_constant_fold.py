"""LEC-KEEP-CFOLD 11-11 (DIE-QC-97 helper; class shared by QC glue and S81 dsdv_slice_c1x_C t6/t7/t8): KEEP FAIL
because synthesis folded a kept no-reset register that only ever loads one constant into a tie cell.
  QC glue: 7 of 16280 kept bits, u_sys_face.cfg_data__ot_q[6..9,16,30,31] ((* keep *) pin register, D = a
           u_lp_data shift register loaded only with 0); the gate drives each name from TIELO.
  S81 t8:  32 of 39116 kept bits, u_xg.u_s.u_ctl.g_hq[k].h[...] (D = load ? r3_b0[bit] : h, r3_b0 <- r2_b0 <- an
           arithmetic bit that is always the constant); the gate drives them from TIELO / TIEHI (h[5] of g_hq[2..4]).
Yosys opt_dff folds such a register even with (* keep *) (it extracts the enable first, LEC-S81-3 11-10), so the
keep attribute cannot be the fix and the bit needs no flop: kept_constant_folds proves the constant (with the
gold-only registers it loads from) by one combinational check and the kept check reports it, not fails it.
A live kept bit (data load, merged twin, wrong constant) stays missing.
    python3 -m pytest -q tools/die_plan/test_lec_kept_constant_fold.py"""
import shutil
import subprocess

import pytest

import lec
from test_lec import _seq, _sim_prove

hold = lambda m, e, d, q: m.AND(m.AND(e, d) ^ 1, m.AND(e ^ 1, q) ^ 1) ^ 1           # e ? d : q


def _design(tmp_path, h_next, r_next=None, gate_h=0, keep="lec_top/u_dut.h\n"):
    """gold: kept h (D = h_next), gold-only r (D = r_next, default: loads 0), observer o = h ^ d.
    gate: o only, o' = gate_h ^ d (h tied to gate_h by synthesis)."""
    kf = tmp_path / "gold.keep"
    kf.write_text(keep)
    r_next = r_next or (lambda m, l: hold(m, l["e"], 0, l["r"]))
    g, gm = _seq(tmp_path, "g", ["d", "e"], ["h", "r", "o"],
                 lambda m, l: {"h": h_next(m, l), "r": r_next(m, l), "o": m.XOR(l["h"], l["d"])})
    t, tm = _seq(tmp_path, "t", ["d", "e"], ["o"], lambda m, l: {"o": m.XOR(gate_h, l["d"])})
    return lec.Lec(g, gm, t, tm), kf


def _missing(L, kf):
    declared, missing, const = lec.kept_registers(L, kf)
    assert declared == ["ff:u_dut.h"] and not const
    return missing


def test_chain_folded_bit_is_constant_not_missing(tmp_path):
    """S81 g_hq shape: h <= e ? (r & d) : h with r <= e ? 0 : r.  h is a constant only together with r."""
    L, kf = _design(tmp_path, lambda m, l: hold(m, l["e"], m.AND(l["r"], l["d"]), l["h"]))
    miss = _missing(L, kf)
    assert miss == ["ff:u_dut.h"]
    assert lec.kept_constant_folds(L, miss) == {"ff:u_dut.h": 0}


def test_tiehi_fold_is_found_by_flipping(tmp_path):
    """S81 g_hq[2].h[5] shape: the register only ever loads 1 (gate TIEHI)."""
    L, kf = _design(tmp_path, lambda m, l: hold(m, l["e"], l["r"], l["h"]),
                    r_next=lambda m, l: hold(m, l["e"], 1, l["r"]), gate_h=1)
    assert lec.kept_constant_folds(L, _missing(L, kf)) == {"ff:u_dut.h": 1}


def test_non_structural_constant_needs_the_prover(tmp_path, monkeypatch):
    """D = e ? (d & (~d & r')) : h is 0 for every input but not by structural hashing: without a prover (work=None)
    the bit is refused (fail closed); with the prover it is proved."""
    nx = lambda m, l: hold(m, l["e"], m.AND(l["d"], m.AND(l["d"] ^ 1, l["o"])), l["h"])
    L, kf = _design(tmp_path, nx)
    miss = _missing(L, kf)
    assert lec.kept_constant_folds(L, miss) == {}
    monkeypatch.setattr(lec, "prove", _sim_prove)
    assert lec.kept_constant_folds(L, miss, tmp_path) == {"ff:u_dut.h": 0}


def test_live_data_bit_stays_missing(tmp_path, monkeypatch):
    """mutant: h loads live data (a kept pin register / fan-out copy of a live bit): refuted, still KEEP FAIL."""
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L, kf = _design(tmp_path, lambda m, l: hold(m, l["e"], l["d"], l["h"]))
    miss = _missing(L, kf)
    assert lec.kept_constant_folds(L, miss, tmp_path) == {}


def test_source_that_loads_both_constants_stays_missing(tmp_path, monkeypatch):
    """mutant: r loads d's value class (0 or 1), so h is not a constant: refused under both proposals."""
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L, kf = _design(tmp_path, lambda m, l: hold(m, l["e"], l["r"], l["h"]),
                    r_next=lambda m, l: hold(m, l["e"], l["d"], l["r"]))
    assert lec.kept_constant_folds(L, _missing(L, kf), tmp_path) == {}


def test_merged_twin_is_not_a_constant_fold(tmp_path, monkeypatch):
    """mutant: the classic merge (kept copy h2 of h, same D = d, only h survives in the gate) is not exempted here;
    it stays for kept_merged_twins / KEEP FAIL."""
    monkeypatch.setattr(lec, "prove", _sim_prove)
    kf = tmp_path / "gold.keep"
    kf.write_text("lec_top/u_dut.h\nlec_top/u_dut.h2\n")
    g, gm = _seq(tmp_path, "g", ["d"], ["h", "h2", "o"],
                 lambda m, l: {"h": l["d"], "h2": l["d"], "o": m.XOR(l["h"], l["h2"])})
    t, tm = _seq(tmp_path, "t", ["d"], ["h", "o"], lambda m, l: {"h": l["d"], "o": 0})
    L = lec.Lec(g, gm, t, tm)
    declared, missing, _ = lec.kept_registers(L, kf)
    assert missing == ["ff:u_dut.h2"]
    assert lec.kept_constant_folds(L, missing, tmp_path) == {}


def test_matched_register_is_never_assumed(tmp_path, monkeypatch):
    """h <= e ? o : h where o is a live register that exists in the gate: o is never put in the constant set, so h is
    refused (the fold may not assume anything about a register the gate still has)."""
    monkeypatch.setattr(lec, "prove", _sim_prove)
    L, kf = _design(tmp_path, lambda m, l: hold(m, l["e"], l["o"], l["h"]))
    assert lec.kept_constant_folds(L, _missing(L, kf), tmp_path) == {}


YOSYS_SRC = """
module t(input ck, input e, input d, output o);
  reg r;
  (* keep *) reg h;
  always @(posedge ck) if (e) r <= 1'b0;
  always @(posedge ck) if (e) h <= r & d;
  assign o = h ^ d;
endmodule
"""


def test_yosys_folds_a_kept_constant_loading_register(tmp_path):
    """the premise, on the real tool: (* keep *) on h does not stop yosys from replacing h (and r) by a constant,
    so a keep attribute in the synth recipe is not a fix for this class.  Control: the same kept h loading live
    data d keeps its flop (so the count below does see flops)."""
    import re
    exe = shutil.which("yosys")
    if not exe:
        pytest.skip("yosys required")

    def flops(src, name):
        (tmp_path / f"{name}.v").write_text(src)
        r = subprocess.run([exe, "-q", "-p", f"read_verilog {name}.v; synth -top t -flatten; opt_dff; opt_clean; "
                                             f"tee -q -o {name}.stat stat"],
                           cwd=tmp_path, capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stderr[-500:]
        txt = (tmp_path / f"{name}.stat").read_text()
        # yosys prints '<n> <cell>' (0.4x+) or '<cell> <n>' (older): count either order
        return sum(int(a or b) for a, b in re.findall(r"(?:(\d+)\s+\$_\w*DFF\w*_)|(?:\$_\w*DFF\w*_\s+(\d+))", txt))

    assert flops(YOSYS_SRC, "fold") == 0
    assert flops(YOSYS_SRC.replace("h <= r & d", "h <= d"), "live") == 1
