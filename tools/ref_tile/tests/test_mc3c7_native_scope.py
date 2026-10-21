"""COORD 10-20 20:05: census <=56 loads admitted ONLY for the two MC3c7 kits."""
import copy
import json
from pathlib import Path
import pytest
import native_census as N
import pre_route_gate as P


def actual():
    return json.loads((Path(__file__).parent / 'fixtures/mc3c7_native_r2_cts.json').read_text())


def out(r):
    return 'GATE_NATIVE_CENSUS_RESULT ' + json.dumps(r)


@pytest.mark.parametrize('kit', sorted(N.MC3C7_KITS))
def test_scoped_kits_admit_with_warning_and_raw_fail(kit):
    r = actual()
    r['kit'] = kit
    before = copy.deepcopy(r)
    assert N.mc3c7_scoped_admission(r, kit)
    g = P.Gate()
    assert P.check_native_census(g, out(r), kit)
    assert r == before and r['status'] == 'FAIL' and r['max_dynamic_loads'] == 55
    assert any(i['severity'] == 'WARN' for i in g.items)


@pytest.mark.parametrize('kit', ['hdie_pc_ctrl_mc3c6_t242', 'hdie_pc_ctrl_h9c', 'hdie_pc_ctrl_mc3c7_wel_x', 'other'])
def test_other_kits_still_refuse(kit):
    r = actual()
    r['kit'] = kit
    assert not N.mc3c7_scoped_admission(r, kit)
    assert not P.check_native_census(P.Gate(), out(r), kit)


@pytest.mark.parametrize('change', ['gate_kit_mismatch', 'no_gate_kit', 'no_report_kit', 'top', 'over56',
                                    'max', 'role_error', 'limit', 'raw_pass', 'schema', 'netlist'])
def test_outside_scope_refuses(change):
    r = actual()
    kit = 'hdie_pc_ctrl_mc3c7_cts'
    if change == 'gate_kit_mismatch': kit = 'hdie_pc_ctrl_mc3c6_t242'
    elif change == 'no_gate_kit': kit = None
    elif change == 'no_report_kit': r.pop('kit')
    elif change == 'top': r['top'] += '_other'
    elif change == 'over56': r['violations'][0]['loads'] = 57
    elif change == 'max': r['max_dynamic_loads'] = 57
    elif change == 'role_error': r['role_errors'] = ['x']
    elif change == 'limit': r['limit'] = 56
    elif change == 'raw_pass': r['status'] = 'PASS'
    elif change == 'schema': r['schema'] += '_x'
    elif change == 'netlist': r['netlist']['sha256'] = 'z'
    if kit is not None:
        assert not N.mc3c7_scoped_admission(r, kit)
    assert not P.check_native_census(P.Gate(), out(r), kit)


def test_ktree_scope_unchanged_for_mc3c7_receipt():
    assert not N.ktree_scoped_admission(actual())
