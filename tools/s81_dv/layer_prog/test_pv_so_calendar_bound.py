"""S81-PLAN-1: plan_halves_bound books the BOUND cross-half lane ages; +-1 / as-built / missing lanes are caught."""
import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pv_so_calendar as C


def bind(e_w=20, w_e=20):
    mk = lambda a, b, n: dict(lane=f'attn__{a}__{b}', bound_stages=n, plan_cycles=n, asbuilt_stages=[26, 26])
    return dict(die='toy', buses=[mk('svc_11', 'svc_5', e_w), mk('svc_5', 'svc_11', w_e)])


def run(b):
    return C.plan_halves_bound(b, 'svc_11', 'svc_5', 18, 18, 100, 100, 50, 0)


def test_bound_ages_and_shift():
    r = run(bind())
    assert r['route_age'] == dict(E_E=18, W_W=18, E_W=20, W_E=20)
    for d in (1, -1):
        r2 = run(bind(e_w=20 + d))
        assert r2['route_age']['E_W'] == 20 + d and r2 != r


def test_fail_closed():
    b = bind()
    b['buses'][0]['plan_cycles'] = 26          # bind disagrees with the plan
    with pytest.raises(ValueError):
        run(b)
    b = bind()
    b['buses'].pop()
    with pytest.raises(ValueError):
        run(b)
