"""Constant-connected identities use the authentic loaded ASAP7 functions."""
import hashlib
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_census as N


@pytest.fixture(scope='module')
def roles():
    lib = Path(__file__).resolve().parents[3] / 'physical/asap7_stdcell_native_models/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib'
    assert hashlib.sha256(lib.read_bytes()).hexdigest() == 'fa92e6ab1481810602811b1eea54bc016a341f11fb5188d7512c026599adf038'
    cells, _ = N.liberty_roles([lib])
    # Endpoint-only fixture; the identities under review use official functions.
    cells['ENDPOINT'] = {'sequential': True, 'pins': {
        'CK': {'direction': 'input', 'clock': True, 'function': None},
        'D': {'direction': 'input', 'clock': False, 'function': None}}}
    return cells


def run(roles, master, tie, n=33, prefix='', y=False):
    text = 'module top(ck,d,e,y); input ck,d,e; output y; wire b,t;\n' + prefix
    text += f'{master} gate(.A(d),.B({tie}),.Y(b));\n'
    for i in range(n):
        text += f'ENDPOINT f{i}(.CK(ck),.D(b));\n'
    text += ('assign y=b;' if y else '') + 'endmodule'
    graph, _ = N.TL.flatten(N.TL.parse_verilog(text), 'top')
    return N.census(graph, roles)


@pytest.mark.parametrize('master,tie,inverted', [
    ('AND2x2_ASAP7_75t_R', "1'b1", False),
    ('OR2x2_ASAP7_75t_R', "1'b0", False),
    ('NAND2x2_ASAP7_75t_R', "1'b1", True),
    ('NOR2x2_ASAP7_75t_R', "1'b0", True),
])
def test_actual_constant_input_identities_attribute_to_producer(roles, master, tie, inverted):
    result = run(roles, master, tie)
    assert not result['role_errors']
    assert result['violations'][0]['driver'] == 'd'
    assert result['violations'][0]['loads'] == 33
    assert result['constant_input_transparent_cells'][0]['inverted'] is inverted
    assert result['constant_input_transparent_cells'][0]['constant_inputs'][0]['source']['kind'] == 'literal'
    physical = {r['driver']: r['loads'] for r in result['physical_nonclock_driver_counts']}
    assert physical['d'] == 1 and physical['gate/Y'] == 33


def test_actual_tie_function_provenance_and_no_false_constant_from_tied_pin(roles):
    result = run(roles, 'AND2x2_ASAP7_75t_R', 't', prefix='TIEHIx1_ASAP7_75t_R hi(.H(t));', y=True)
    assert result['violations'][0]['driver'] == 'd'
    assert result['violations'][0]['loads'] == 34
    source = result['constant_input_transparent_cells'][0]['constant_inputs'][0]['source']
    assert source['instance'] == 'hi' and source['function'] == '1'
    assert result['constant_output_bits'] == []


def test_actual_two_variable_function_remains_a_real_root(roles):
    result = run(roles, 'AND2x2_ASAP7_75t_R', 'e')
    assert result['constant_input_transparent_cells'] == []
    assert result['violations'][0]['driver'] == 'gate/Y'
    assert result['violations'][0]['loads'] == 33


@pytest.mark.parametrize('master,tie', [
    ('AND2x2_ASAP7_75t_R', "1'b1"),
    ('OR2x2_ASAP7_75t_R', "1'b0"),
    ('NAND2x2_ASAP7_75t_R', "1'b1"),
    ('NOR2x2_ASAP7_75t_R', "1'b0"),
    ('AND2x2_ASAP7_75t_R', 'e'),
])
def test_distributed_identities_cannot_hide_40_load_producer(roles, master, tie):
    text = 'module top(ck,d,e); input ck,d,e;\n'
    for branch in range(2):
        text += f'{master} g{branch}(.A(d),.B({tie}),.Y(b{branch}));\n'
        for i in range(20):
            text += f'ENDPOINT f{branch}_{i}(.CK(ck),.D(b{branch}));\n'
    text += 'endmodule'
    graph, _ = N.TL.flatten(N.TL.parse_verilog(text), 'top')
    result = N.census(graph, roles)
    physical = {r['driver']: r['loads'] for r in result['physical_nonclock_driver_counts']}
    assert physical['d'] == 2 and physical['g0/Y'] == physical['g1/Y'] == 20
    if tie == 'e':
        assert result['status'] == 'PASS' and not result['constant_input_transparent_cells']
    else:
        assert result['status'] == 'FAIL'
        assert result['violations'][0]['driver'] == 'd'
        assert result['violations'][0]['loads'] == 40


def test_constant_function_reduction_reports_actual_inputs(roles):
    result = run(roles, 'AND2x2_ASAP7_75t_R', "1'b0", y=True)
    assert result['status'] == 'PASS'
    assert result['constant_output_bits'][0]['source']['master'] == 'AND2x2_ASAP7_75t_R'
    assert result['constant_output_bits'][0]['source']['constant_inputs'][0]['value'] == 0
    assert result['functional_pin_contract'] == 'NOT_EVALUATED'


def test_constant_propagation_is_order_independent_and_retains_unary_path(roles):
    text = '''module top(d,y); input d; output y; wire t,u;
      AND2x2_ASAP7_75t_R gate(.A(d),.B(u),.Y(y));
      NOR2x2_ASAP7_75t_R inv(.A(t),.B(1'b0),.Y(u));
      TIELOx1_ASAP7_75t_R lo(.L(t)); endmodule'''
    graph, _ = N.TL.flatten(N.TL.parse_verilog(text), 'top')
    result = N.census(graph, roles)
    assert result['constant_output_bits'] == []
    reduction = next(r for r in result['constant_input_transparent_cells'] if r['instance'] == 'gate')
    assert reduction['constant_inputs'][0]['value'] == 1
    assert reduction['constant_inputs'][0]['source']['instance'] == 'inv'


@pytest.mark.parametrize('function', ['A ? B : 0', 'UNKNOWN', 'A &', '__import__(A)', '(0))'])
def test_unknown_function_never_grants_transparency(roles, function):
    candidate = dict(roles)
    role = dict(roles['AND2x2_ASAP7_75t_R'])
    role['pins'] = dict(role['pins']); role['pins']['Y'] = dict(role['pins']['Y'], function=function)
    candidate['AND2x2_ASAP7_75t_R'] = role
    result = run(candidate, 'AND2x2_ASAP7_75t_R', "1'b1")
    assert result['constant_input_transparent_cells'] == []
    assert result['violations'][0]['driver'] == 'gate/Y'


@pytest.mark.parametrize('master,pins', [
    ('TIEHIx1_ASAP7_75t_R', {'H': "1'0"}),
    ('AND2x2_ASAP7_75t_R', {'A': "1'1", 'B': "1'1", 'Y': "1'0"}),
])
def test_conflicting_literal_and_actual_constant_function_refuse_with_both_sources(roles, master, pins):
    graph = N.TL.Graph()
    graph.cells = [(master, 'conflict', {p: [graph.net(n)] for p, n in pins.items()})]
    result = N.census(graph, roles)
    assert result['status'] == 'FAIL'
    assert any('contradictory known constant' in e for e in result['role_errors'])
    conflict = result['constant_conflicts'][0]
    assert conflict['existing'] == {'value': 0, 'source': {'kind': 'literal', 'net': "1'0"}}
    assert conflict['conflicting']['value'] == 1
    assert conflict['conflicting']['source']['master'] == master


def test_top_input_alias_to_literal_is_not_silently_a_proven_tie(roles):
    graph, _ = N.TL.flatten(N.TL.parse_verilog("module top(d); input d; assign d=1'b0; endmodule"), 'top')
    result = N.census(graph, roles)
    assert result['status'] == 'FAIL'
    assert any('dynamic driver aliased to known constant' in e for e in result['role_errors'])
    assert result['constant_conflicts'][0]['conflicting_dynamic_driver'] == {'kind': 'input_port', 'port': 'd'}


def test_dynamic_cell_output_alias_to_literal_refuses(roles):
    graph, _ = N.TL.flatten(N.TL.parse_verilog('''module top(a,b); input a,b;
        AND2x2_ASAP7_75t_R dynamic(.A(a),.B(b),.Y(1'b0)); endmodule'''), 'top')
    result = N.census(graph, roles)
    assert result['status'] == 'FAIL'
    conflict = result['constant_conflicts'][0]
    assert conflict['conflicting_dynamic_driver']['instance'] == 'dynamic'
    assert conflict['existing']['source']['kind'] == 'literal'
