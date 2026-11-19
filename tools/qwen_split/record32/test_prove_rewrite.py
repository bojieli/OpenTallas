"""prove_rewrite.py: registers pair by hierarchical name; a missing partner or a different reset kind is refused."""
import importlib.util
from pathlib import Path

import pytest

S = importlib.util.spec_from_file_location("prove_rewrite", Path(__file__).with_name("prove_rewrite.py"))
P = importlib.util.module_from_spec(S); S.loader.exec_module(P)


def mod(gate, ffname='u.r', fftype='$_DFF_PN0_', base=0):
    b = lambda x: x + base
    cells = {'g': {'type': gate, 'connections': {'A': [b(3)], 'B': [b(6)], 'Y': [b(5)]}, 'port_directions': {'A': 'input', 'B': 'input', 'Y': 'output'}},
             '$ff$' + str(base): {'type': fftype, 'connections': {'C': [b(2)], 'D': [b(5)], 'Q': [b(6)], 'R': [b(4)]},
                                  'port_directions': {'C': 'input', 'D': 'input', 'Q': 'output', 'R': 'input'}}}
    ports = {'ck': {'direction': 'input', 'bits': [b(2)]}, 'a': {'direction': 'input', 'bits': [b(3)]},
             'rst_rn': {'direction': 'input', 'bits': [b(4)]}, 'q': {'direction': 'output', 'bits': [b(6)]}}
    return {'ports': ports, 'cells': cells, 'netnames': {ffname: {'bits': [b(6)], 'hide_name': 0}}}


def test_miter_pairs_registers_by_name_across_different_bit_numbers():
    text, n, k = P.build(mod('$_AND_'), mod('$_AND_', base=40))
    assert n == 2 and k == 4 and 'module record32_rewrite' in text and text.count('assign bad=') == 1


def test_register_without_partner_is_refused():
    with pytest.raises(AssertionError):
        P.build(mod('$_AND_'), mod('$_AND_', ffname='u.other'))


def test_different_reset_value_is_refused():
    with pytest.raises(AssertionError):
        P.build(mod('$_AND_'), mod('$_AND_', fftype='$_DFF_PN1_'))
