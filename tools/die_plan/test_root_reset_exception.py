"""The whole-die asynchronous reset exception must never mask forwarded reset."""
import copy
import sys
from pathlib import Path

import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys
import reset_tree
import schema
from test_sdc_lint import TINY, _kit, _errs


def test_two_root_reset_pins_only():
    text, ctx = _kit(TINY)
    ctx['root_async_reset'] = True
    assert _errs(text + gen_phys.ROOT_RESET_FALSE_PATH + '\n', ctx) == []
    assert _errs(text, ctx)
    assert _errs(text + (gen_phys.ROOT_RESET_FALSE_PATH + '\n') * 2, ctx)


@pytest.mark.parametrize('old,new', [('u_rst_root','u_rst_in'), ('/RESETN','/D'),
    ('p\\[[01]\\]','.*'), ('[get_ports {arst_n}]','[all_inputs]')])
def test_forwarded_reset_and_broad_waiver_mutants_fail(old,new):
    text, ctx = _kit(TINY)
    ctx['root_async_reset'] = True
    assert _errs(text + gen_phys.ROOT_RESET_FALSE_PATH.replace(old,new) + '\n', ctx)


def test_receiver_context_cannot_carry_exception():
    text, ctx = _kit(TINY)
    assert _errs(text + gen_phys.ROOT_RESET_FALSE_PATH + '\n', ctx)


def test_root_role_and_replication_fail_closed(monkeypatch):
    raw = copy.deepcopy(TINY)
    raw['reset']['release'] = 'wavefront'
    p = schema.Plan(raw)
    root = next(iter(p.types))
    monkeypatch.setattr(reset_tree, 'wf_solve', lambda p: {'root_type': root})
    assert gen_phys.root_async_reset(p, root)
    for tn in p.types:
        if tn != root:
            assert not gen_phys.root_async_reset(p, tn)
    p.parts['duplicate_root'] = {'type': root}
    with pytest.raises(ValueError, match='unique root'):
        gen_phys.root_async_reset(p, root)
