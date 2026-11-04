"""self_hold_reset: the one no-load-path constant (COORD 11-04, S81 leaf LEC form 1), with its negative controls."""
import unittest
import lec
from lec import self_hold_reset


def aig(n_inputs, n_latches, ands, nexts):
    return {"I": n_inputs, "L": n_latches, "A": len(ands) // 2, "ands": list(ands), "latches": list(nexts)}


class SelfHold(unittest.TestCase):
    # vars: 1 = rn (input), 2 = en (input), 3 = q (latch); ands from var 4
    Q, RN, EN = 6, 2, 4

    def test_async_reset_to_zero_with_no_load_is_constant(self):
        d = aig(2, 1, [self.RN, self.Q], [8])                      # D = rn & q
        self.assertEqual(self_hold_reset(d, self.Q, 0), (1, 0))

    def test_set_to_one_is_constant(self):
        # D = !rn | q = !(rn & !q)
        d = aig(2, 1, [self.RN, self.Q ^ 1], [9])
        self.assertEqual(self_hold_reset(d, self.Q, 1), (1, 0))
        self.assertIsNone(self_hold_reset(d, self.Q, 0))           # it can leave 0

    def test_dead_enable_folds_out_of_the_support(self):
        # D = rn & ((0 & en) | q): var 4 = 0 & en, var 5 = !v4 & !q, var 6 = rn & !v5
        d = aig(2, 1, [0, self.EN, 9, self.Q ^ 1, self.RN, 11], [12])
        self.assertEqual(self_hold_reset(d, self.Q, 0), (1, 0))

    def test_load_path_is_not_constant(self):
        # D = rn & (en | q): the negative control, a register that a load can set
        d = aig(2, 1, [self.EN ^ 1, self.Q ^ 1, self.RN, 9], [10])
        self.assertIsNone(self_hold_reset(d, self.Q, 0))

    def test_no_reset_is_not_constant(self):
        self.assertIsNone(self_hold_reset(aig(2, 1, [], [self.Q]), self.Q, 0))     # D = q: X power-up

    def test_register_not_read_is_not_this_rule(self):
        self.assertIsNone(self_hold_reset(aig(2, 1, [self.RN, self.EN], [8]), self.Q, 0))

    def test_inverted_literal(self):
        d = aig(2, 1, [self.RN, self.Q], [8])
        self.assertEqual(self_hold_reset(d, self.Q ^ 1, 1), (1, 0))    # !q is constant 1


if __name__ == "__main__":
    unittest.main()


def test_self_hold_needs_a_real_async_reset_to_the_same_value():
    """D = en ? 0 : Q with no async reset (a sync load on any input) is the 'hold' mutant: never a constant"""
    import types
    k = "ff:r"
    d = {"I": 1, "L": 1, "A": 0, "ands": []}

    def hit(regs, c):
        L = types.SimpleNamespace(gold=d, gate=d, gp={k: 4}, tp={k: 4}, async_reset_regs={"gold": regs})
        return lec._noreset_self_hold(L, "gold", k, c)

    saved = lec.self_hold_reset
    lec.self_hold_reset = lambda *a, **kw: (1, 0)
    try:
        assert hit({}, 0) is None
        assert hit({k: (1, "rst")}, 0) is None
        got = hit({k: (0, "rst")}, 0)
        assert got["value"] == 0 and got["async_net"] == "rst"
    finally:
        lec.self_hold_reset = saved


def test_async_resets_read_from_the_async2sync_log(tmp_path):
    log = tmp_path / "x.log"
    log.write_text(
        "Replacing lec_top.u.a_q$_ALDFF_PN_ ($_ALDFF_PN_): ALOAD=\\\\u.q [594], AD=1'0, D=\\\\u.a_q, Q=\\\\u.a_q\n"
        "Replacing lec_top.u.b_q$_ALDFF_PN_ ($_ALDFF_PN_): ALOAD=\\\\u.en, AD=\\\\u.v, D=\\\\u.d, Q=\\\\u.b_q\n"
        "Replacing lec_top.u.c[3]$_DFFE_PN0P_.IQN$_DFFSR_PPP_ ($_DFFSR_PPP_): SET=x, CLR=y, D=z, Q=w\n"
        "Replacing lec_top.u.e$_DFF_PN1_.IQN$_DFFSR_PPP_ ($_DFFSR_PPP_): SET=x, CLR=y, D=z, Q=w\n"
        "Replacing lec_top.$flatten\\\\u.c[3]$_DFFE_PN0P_.$auto$liberty.cc:242:create_ff$1 ($_DFFSR_PPP_): SET=x\n")
    got = lec.read_async_resets(log, tmp_path / "missing.log")
    assert got["ff:u.a_q"] == (0, "u.q [594]")
    assert "ff:u.b_q" not in got
    assert got["ff:u.c[3]"] == (0, None)
    assert got["ff:u.e"] == (1, None)
    assert len(got) == 3
