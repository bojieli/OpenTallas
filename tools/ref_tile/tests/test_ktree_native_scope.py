"""The coordinator exception admits only the complete reviewed mapped image."""
import copy
import json
from pathlib import Path
import pytest
import native_census as N
import pre_route_gate as P


def actual():
    return json.loads((Path(__file__).parent / 'fixtures/ktree_native_0330.json').read_text())


def test_reviewed_actual_receipt_keeps_raw_fail_and_reports_warning():
    r = actual()
    before = copy.deepcopy(r)
    assert N.ktree_scoped_admission(r)
    g = P.Gate()
    assert P.check_native_census(g, 'GATE_NATIVE_CENSUS_RESULT ' + json.dumps(r))
    assert r == before and r['status'] == 'FAIL' and r['max_dynamic_loads'] == 34
    assert any(item['severity'] == 'WARN' for item in g.items)


@pytest.mark.parametrize('change', [
    'top', 'netlist', 'liberty', 'missing_liberty', 'duplicate_liberty',
    'missing_node', 'extra_node', 'driver', 'net', 'sequential', 'reset',
    'loads', 'max', 'role_error', 'limit', 'raw_status', 'schema',
])
def test_outside_exact_source_image_or_nodes_refuses(change):
    r = actual()
    if change == 'top': r['top'] += '_other'
    elif change == 'netlist': r['netlist']['sha256'] = 'a' * 64
    elif change == 'liberty': r['liberty'][0]['sha256'] = 'a' * 64
    elif change == 'missing_liberty': r['liberty'].pop()
    elif change == 'duplicate_liberty': r['liberty'].append(r['liberty'][0])
    elif change == 'missing_node': r['violations'].pop()
    elif change == 'extra_node': r['violations'].append(r['violations'][0])
    elif change == 'driver': r['violations'][0]['driver'] += '_other'
    elif change == 'net': r['violations'][0]['net'] += '_other'
    elif change == 'sequential': r['violations'][0]['driver_role'] = 'sequential'
    elif change == 'reset': r['violations'][0]['driver'] = 'rst_n'
    elif change == 'loads': r['violations'][0]['loads'] = 35
    elif change == 'max': r['max_dynamic_loads'] = 35
    elif change == 'role_error': r['role_errors'] = ['missing actual Liberty role']
    elif change == 'limit': r['limit'] = 36
    elif change == 'raw_status': r['status'] = 'PASS'
    elif change == 'schema': r['schema'] += '_other'
    assert not N.ktree_scoped_admission(r)
    assert not P.check_native_census(P.Gate(), 'GATE_NATIVE_CENSUS_RESULT ' + json.dumps(r))


def test_self_declared_admission_has_no_authority():
    r = actual()
    r['netlist']['sha256'] = 'a' * 64
    r['admission'] = {'status': 'PASS_WITH_SCOPED_WAIVER', 'authority': N.KTREE_SCOPE}
    assert not P.check_native_census(P.Gate(), 'GATE_NATIVE_CENSUS_RESULT ' + json.dumps(r))
