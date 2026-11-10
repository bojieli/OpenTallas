"""COORD 11-09 loopgap-153x-1109: census <=64 loads admitted for the S81 svc provider kits (s81svc_*) only."""
import copy
import json
from pathlib import Path
import pytest
import native_census as N
import pre_route_gate as P


def actual():
    r = json.loads((Path(__file__).parent / 'fixtures/mc3c7_native_r2_cts.json').read_text())
    r['kit'] = 's81svc_irg_hsfp'
    r['top'] = 'ot_hdc_v41x_idx_hslice_fp'
    r['violations'][0]['loads'] = 64
    r['max_dynamic_loads'] = 64
    return r


def out(r):
    return 'GATE_NATIVE_CENSUS_RESULT ' + json.dumps(r)


def test_scoped_kit_admits_with_warning_and_raw_fail():
    r = actual()
    before = copy.deepcopy(r)
    assert N.s81svc_scoped_admission(r, 's81svc_irg_hsfp')
    g = P.Gate()
    assert P.check_native_census(g, out(r), 's81svc_irg_hsfp')
    assert r == before and r['status'] == 'FAIL'
    assert any(i['severity'] == 'WARN' for i in g.items)


@pytest.mark.parametrize('change', ['over64', 'max', 'gate_kit_mismatch', 'no_gate_kit', 'other_kit', 'bare_prefix',
                                    'role_error', 'limit', 'raw_pass', 'schema', 'netlist'])
def test_outside_scope_refuses(change):
    r = actual()
    kit = 's81svc_irg_hsfp'
    if change == 'over64': r['violations'][0]['loads'] = 65
    elif change == 'max': r['max_dynamic_loads'] = 65
    elif change == 'gate_kit_mismatch': kit = 's81svc_other'
    elif change == 'no_gate_kit': kit = None
    elif change == 'other_kit': r['kit'] = kit = 'hdie_pc_ctrl_h9c'
    elif change == 'bare_prefix': r['kit'] = kit = 's81svc_'
    elif change == 'role_error': r['role_errors'] = ['x']
    elif change == 'limit': r['limit'] = 64
    elif change == 'raw_pass': r['status'] = 'PASS'
    elif change == 'schema': r['schema'] += '_x'
    elif change == 'netlist': r['netlist']['sha256'] = 'z'
    if kit is not None:
        assert not N.s81svc_scoped_admission(r, kit)
    assert not P.check_native_census(P.Gate(), out(r), kit)


def test_scope_bound_to_spec():
    r = actual()
    assert P.check_native_census(P.Gate(), out(r), P.native_scope_kit(Path('/k/s81svc_irg_hsfp'),
                                                                        {'name': 's81svc_irg_hsfp', 'top': r['top']}))
    assert not P.check_native_census(P.Gate(), out(r), P.native_scope_kit(Path('/k/s81svc_irg_hsfp'),
                                                                            {'name': 'other', 'top': r['top']}))
