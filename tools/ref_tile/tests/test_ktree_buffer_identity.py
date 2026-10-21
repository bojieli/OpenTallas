"""Causal fixed-image tests for the reviewed positive-BUF identity mechanism."""
import copy
import hashlib
import pytest
import native_census as N
import pre_route_gate as P
from test_ktree_native_scope import actual


def role():
    return {'sequential': False, 'bus_order': {}, 'pins': {
        'A': {'direction': 'input', 'clock': False, 'function': None},
        'Y': {'direction': 'output', 'clock': False, 'function': 'A'}}}


def buf(name='_100_', master='BUFx2', a='a', y='b'):
    return f'  {master} {name} (\n    .A({a}),\n    .Y({y})\n  );'


def image(rows=None):
    return ('module top(a, b, c);\n  input a;\n  output b;\n  wire c;\n' +
            '\n'.join(rows or [buf(), buf('_101_', a='b', y='c')]) + '\nendmodule\n').encode()


def canonical(raw, roles=None):
    return N.ktree_positive_buf_canonical(raw, roles or {'BUFx2': role(), 'BUFx3': role()})[0]


def test_only_buffer_identity_and_complete_statement_order_omitted():
    assert canonical(image()) == canonical(image([buf('_900_', a='b', y='c'), buf('_901_')]))
    assert canonical(image()) != canonical(image() + b'// context changed\n')
    assert canonical(image()) != canonical(image([buf(master='BUFx3'), buf('_101_', a='b', y='c')]))
    assert canonical(image()) != canonical(image([buf(a='c'), buf('_101_', a='b', y='c')]))
    assert canonical(image()) != canonical(image([buf()]))
    assert canonical(image()) != canonical(image().replace(b'input a;', b'input a;\n  wire unused;'))


@pytest.mark.parametrize('change', ['attr', 'duplicate_buf', 'duplicate_other_master',
    'pin', 'pin_order', 'missing_pin', 'extra_pin', 'syntax', 'hierarchy', 'spaced_hierarchy', 'local_reference'])
def test_unsupported_or_ambiguous_identity_refuses(change):
    raw = image()
    if change == 'attr': raw = raw.replace(b'  BUFx2', b'  (* keep = 1 *)\n  BUFx2', 1)
    elif change == 'duplicate_buf': raw = raw.replace(b'_101_', b'_100_')
    elif change == 'duplicate_other_master': raw = raw.replace(b'\nendmodule', b'\n  AND2 _100_ (\n    .A(a),\n    .Y(c)\n  );\nendmodule')
    elif change == 'pin': raw = raw.replace(b'.A(a)', b'.Z(a)')
    elif change == 'pin_order': raw = raw.replace(b'.A(a),\n    .Y(b)', b'.A(a)\n    .Y(b),')
    elif change == 'missing_pin': raw = raw.replace(b'    .A(a),\n', b'')
    elif change == 'extra_pin': raw = raw.replace(b'.Y(b)', b'.Y(b),\n    .Z(c)')
    elif change == 'syntax': raw = raw.replace(b'BUFx2 _100_ (', b'BUFx2 custom_id (')
    elif change == 'hierarchy': raw += b'module parent();\n  assign z = child._100_.Y;\nendmodule\n'
    elif change == 'spaced_hierarchy': raw += b'module parent();\n  assign z = child . _100_ . Y;\nendmodule\n'
    elif change == 'local_reference': raw = raw.replace(b'wire c;', b'wire c;\n  assign c = _100_;')
    with pytest.raises(ValueError): canonical(raw)


@pytest.mark.parametrize('change', ['missing', 'function', 'inverter', 'clock', 'state', 'bus', 'extra_contact'])
def test_actual_library_positive_unary_role_required(change):
    r = role()
    roles = {'BUFx2': r}
    if change == 'missing': roles = {'other': r}
    elif change == 'function': r['pins']['Y']['function'] = '0'
    elif change == 'inverter': r['pins']['Y']['function'] = '!A'
    elif change == 'clock': r['pins']['A']['clock'] = True
    elif change == 'state': r['sequential'] = True
    elif change == 'bus': r['bus_order'] = {'A': [0]}
    elif change == 'extra_contact': r['pins']['Z'] = copy.deepcopy(r['pins']['A'])
    with pytest.raises(ValueError): canonical(image(), roles)


def test_pinned_canonical_alternative_still_requires_full_exact_scope():
    r = actual()
    r['netlist']['sha256'] = 'f' * 64
    assert not N.ktree_scoped_admission(r)
    r['netlist']['positive_buf_identity_sha256'] = N.KTREE_CANONICAL
    assert N.ktree_scoped_admission(r)
    before = copy.deepcopy(r)
    gate = P.Gate()
    import json
    assert P.check_native_census(gate, 'GATE_NATIVE_CENSUS_RESULT ' + json.dumps(r))
    assert r == before and r['status'] == 'FAIL'
    assert any(item['severity'] == 'WARN' for item in gate.items)
    for change in ('missing_lib', 'node', 'role', 'other_top', 'max', 'canonical'):
        bad = copy.deepcopy(r)
        if change == 'missing_lib': bad['liberty'].pop()
        elif change == 'node': bad['violations'].pop()
        elif change == 'role': bad['role_errors'] = ['unknown pin']
        elif change == 'other_top': bad['top'] += '_other'
        elif change == 'max': bad['max_dynamic_loads'] = 35
        elif change == 'canonical': bad['netlist']['positive_buf_identity_sha256'] = hashlib.sha256(canonical(image())).hexdigest()
        assert not N.ktree_scoped_admission(bad)
