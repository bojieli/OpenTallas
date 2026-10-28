"""LEC-FPREG-7 10-27 (S81 dsdv_bksel_c 6,382 differ): the S81 cores name their ACTIVE-LOW async reset 'rst'
(always @(posedge ck or negedge rst[0])).  The name rule asserted rst = 1, i.e. released, so the LEC reset state reset
nothing and every constant base case failed.  The asserted level is now the level that forces the registers
(structure), decided on gold and applied to the gate; OT_LEC_RESET_POLARITY=name restores the name rule.
    python3 -m pytest -q tools/die_plan/test_lec_reset_polarity.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec  # noqa: E402
from test_lec_memory_layout import _seq  # noqa: E402

REGS = [f"q{i}" for i in range(4)]


def _lec(tmp_path, port, active_low):
    def nxt(m, l):
        on = l[port] if active_low else l[port] ^ 1         # 1 while the reset is released
        return {q: m.AND(on, l["a"] if i == 0 else l[REGS[i - 1]]) for i, q in enumerate(REGS)}
    g, gm = _seq(tmp_path, "gold", [port, "a"], REGS, nxt)
    t, tm = _seq(tmp_path, "gate", [port, "a"], REGS, nxt)
    return lec.Lec(g, gm, t, tm)


def test_active_low_rst_is_asserted_low(tmp_path):
    L = _lec(tmp_path, "rst", active_low=True)
    lec.noreset_classify(L)
    assert L.rst_asserted == {"gold": {"pi:rst[0]": 0}, "gate": {"pi:rst[0]": 0}}
    assert all(L.rst_val[(sd, f"ff:u_dut.{q}")][0] == 0 for sd in ("gold", "gate") for q in REGS)


def test_active_high_rst_keeps_the_name_rule(tmp_path):
    L = _lec(tmp_path, "rst", active_low=False)
    lec.noreset_classify(L)
    assert L.rst_asserted["gold"] == {"pi:rst[0]": 1}
    assert all(L.rst_val[("gold", f"ff:u_dut.{q}")][0] == 0 for q in REGS)


def test_active_low_rst_n_unchanged(tmp_path):
    L = _lec(tmp_path, "rst_n", active_low=True)
    lec.noreset_classify(L)
    assert L.rst_asserted["gold"] == {"pi:rst_n[0]": 0}


def test_name_rule_override_reproduces_the_old_wrong_state(tmp_path, monkeypatch):
    # control: with the old name rule the active-low 'rst' is held released, so no register is reset
    monkeypatch.setenv("OT_LEC_RESET_POLARITY", "name")
    L = _lec(tmp_path, "rst", active_low=True)
    lec.noreset_classify(L)
    assert L.rst_asserted["gold"] == {"pi:rst[0]": 1}
    assert all(L.rst_val[("gold", f"ff:u_dut.{q}")][0] is None for q in REGS)


def test_constant_registers_do_not_mask_the_reset_level(tmp_path):
    # S81 RXsf shape: gold keeps many constant-driven registers (known at either level), so the raw count of known
    # registers is close at both levels; only the registers forced by ONE level decide the polarity.
    consts = [f"k{i}" for i in range(12)]
    def nxt(m, l):
        r = {q: m.AND(l["rst"], l["a"] if i == 0 else l[REGS[i - 1]]) for i, q in enumerate(REGS)}
        r.update({k: 0 for k in consts})
        return r
    g, gm = _seq(tmp_path, "gold", ["rst", "a"], REGS + consts, nxt)
    t, tm = _seq(tmp_path, "gate", ["rst", "a"], REGS, lambda m, l: {q: nxt(m, l)[q] for q in REGS})
    L = lec.Lec(g, gm, t, tm)
    lec.noreset_classify(L)
    assert L.rst_asserted["gold"] == {"pi:rst[0]": 0}
    assert all(L.rst_val[("gate", f"ff:u_dut.{q}")][0] == 0 for q in REGS)
