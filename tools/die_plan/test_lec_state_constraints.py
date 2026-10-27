"""Conditional initialization must be proved, without assigning a value to unreset data."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lec
from test_lec_memory_layout import _seq, _sim_prove


def _design(tmp_path, bad_load=False, no_active_reset=False):
    def gold(m, l):
        active = m.AND(l['start'] ^ 1, l['active'] ^ 1) ^ 1
        if not no_active_reset:
            active = m.AND(l['rn'], active)
        high = m.AND(m.AND(l['start'], int(bad_load)) ^ 1,
                     m.AND(l['start'] ^ 1, l['high']) ^ 1) ^ 1
        return {'active': active, 'high': high, 'o': m.AND(l['active'], l['high'])}
    g, gm = _seq(tmp_path, 'gold', ['rn', 'start'], ['active', 'high', 'o'], gold)
    t, tm = _seq(tmp_path, 'gate', ['rn', 'start'], ['active', 'o'], lambda m, l: {
        'active': m.AND(l['rn'], m.AND(l['start'] ^ 1, l['active'] ^ 1) ^ 1), 'o': 0})
    return lec.Lec(g, gm, t, tm)


HINT = dict(side='gold', keys=['ff:u_dut.active', 'ff:u_dut.high'], allowed=[[0,0], [0,1], [1,0]])


def test_unknown_data_before_start_is_allowed_but_safe_when_active(tmp_path):
    L = _design(tmp_path)
    rec = lec.add_reset_state_constraints(L, [HINT], [])
    assert len(rec['added']) == 1 and rec['added'][0]['reset_values'] == [0, None]
    assert ('gold', 'ff:u_dut.high') not in L.hyp  # no global constant assumption
    m, _ = L.build(with_compare=True, with_hyp=True)
    st = _sim_prove(m)
    assert st['ff:u_dut.o'] == st['cons:gold:ff:u_dut.active'] == 'proved'


def test_mutant_wrong_loaded_value_fails_induction(tmp_path):
    L = _design(tmp_path, bad_load=True)
    assert lec.add_reset_state_constraints(L, [HINT], [])['added']
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert _sim_prove(m)['cons:gold:ff:u_dut.active'] == 'differs'


def test_mutant_no_reset_valid_bit_cannot_supply_a_base_case(tmp_path):
    L = _design(tmp_path, no_active_reset=True)
    rec = lec.add_reset_state_constraints(L, [HINT], [])
    assert rec['rejected'] and L.cons == []
    m, _ = L.build(with_compare=True, with_hyp=True)
    assert _sim_prove(m)['ff:u_dut.o'] == 'differs'


@pytest.mark.parametrize('change', [
    dict(allowed=[[0,0],[1,0]]),             # excludes unknown high=1 while inactive
    dict(keys=['ff:u_dut.missing']),
    dict(keys=['ff:u_dut.active','ff:u_dut.active']),
    dict(allowed=[[0,0],[0,1],[1,2]]),
])
def test_bad_constraint_is_rejected(tmp_path, change):
    L = _design(tmp_path)
    rec = lec.add_reset_state_constraints(L, [dict(HINT, **change)], [])
    assert rec['rejected'] and L.cons == []
