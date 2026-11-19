"""bound_record_graph.py --port-shape: the regenerated netlist keeps the source_copies / rst_leaf ports a parent binds."""
import importlib.util
import json
from pathlib import Path

import pytest

S = importlib.util.spec_from_file_location("brg_shape", Path(__file__).with_name("bound_record_graph.py"))
B = importlib.util.module_from_spec(S); S.loader.exec_module(B)


def design(n_and=70, n_ff=30):
    """en (1 input) gates n_and data bits into flops: en needs copies at 32 loads; all flops on rst_rn[0]"""
    cells = {}; d = list(range(100, 100 + n_and)); y = list(range(300, 300 + n_and)); q = list(range(500, 500 + n_and))
    for i in range(n_and):
        cells[f'a{i}'] = {'type': '$_AND_', 'connections': {'A': [3], 'B': [d[i]], 'Y': [y[i]]},
                          'port_directions': {'A': 'input', 'B': 'input', 'Y': 'output'}}
        cells[f'f{i}'] = {'type': '$_DFF_PN0_', 'connections': {'C': [2], 'D': [y[i]], 'Q': [q[i]], 'R': [4]},
                          'port_directions': {'C': 'input', 'D': 'input', 'Q': 'output', 'R': 'input'}}
    ports = {'ck': {'direction': 'input', 'bits': [2]}, 'en': {'direction': 'input', 'bits': [3]},
             'rst_rn': {'direction': 'input', 'bits': [4]}, 'd': {'direction': 'input', 'bits': d},
             'q': {'direction': 'output', 'bits': q}}
    return json.dumps({'modules': {'top': {'ports': ports, 'cells': cells, 'netnames': {}}}}).encode()


def shape(copies, leaves):
    return {'input_copies': [{'index': i, 'source': ['en', 0]} for i in range(copies)],
            'reset_leaves': [{'index': i, 'source_group': ['rst_rn', 0]} for i in range(leaves)]}


def test_all_provided_copies_and_leaves_are_used():
    text, helpers, r = B.build(design(), 'top', 'top_n32', retain_all_comb=True, shared_helpers=True, port_shape=shape(5, 6))
    assert 'input wire [4:0] source_copies;' in text and 'input wire [5:0] rst_leaf;' in text
    assert [c['index'] for c in r['input_copies']] == list(range(5)) and all(c['direct_sinks'] >= 1 for c in r['input_copies'])
    assert [l['index'] for l in r['reset_leaves']] == list(range(6))
    sizes = [len(l['cells']) for l in r['reset_leaves']]
    assert sum(sizes) == 70 and max(sizes) - min(sizes) <= 1
    cells = r['graph']['cells']
    loads = {}
    for c in cells.values():
        for p, bs in c['connections'].items():
            if c['port_directions'][p] == 'input' and p not in ('C', 'R'):
                for b in bs:
                    loads[b] = loads.get(b, 0) + 1
    nets = [3] + [c['copy_bit'] for c in r['input_copies']]
    assert sum(loads.get(b, 0) for b in nets) == 70 and max(loads.get(b, 0) for b in nets) <= 32


def test_too_few_provided_copies_or_leaves_is_an_error():
    with pytest.raises(ValueError):
        B.build(design(), 'top', 'top_n32', retain_all_comb=True, shared_helpers=True, port_shape=shape(1, 6))
    with pytest.raises(ValueError):
        B.build(design(), 'top', 'top_n32', retain_all_comb=True, shared_helpers=True, port_shape=shape(5, 2))


def test_without_a_shape_the_output_is_the_old_one():
    a = B.build(design(), 'top', 'top_n32', retain_all_comb=True, shared_helpers=True)
    assert 'input wire [1:0] source_copies;' in a[0] and len(a[2]['reset_leaves']) == 3
