import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r8_gate  # noqa: E402

W5 = 'PARAM_REGEN coll_regen.py: W5: r_d of region 0 is not the latest; its r_v would need a pad'
NB = 'PARAM_REGEN coll_regen.py: E2: nb_od of region 0 is not the latest; its nb_oc would need a pad'


def test_r8_stale_and_regen_pad_are_r8_class():
    r8, other = r8_gate.split(['R8_STALE sl_W5_su_c ring_k 3 != 4', W5, NB])
    assert len(r8) == 3 and other == []


def test_other_param_regen_blocks():
    r8, other = r8_gate.split([W5, 'PARAM_REGEN coll_regen.py: W5: lane count 7 != 8'])
    assert len(r8) == 1 and len(other) == 1


def test_unrelated_errors_block():
    r8, other = r8_gate.split([W5, 'UNBOUND port x', 'consumer a != copy depth 3'])
    assert len(r8) == 1 and len(other) == 2
