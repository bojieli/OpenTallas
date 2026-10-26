import copy
import hashlib
import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bound_die import BoundDie, object_items


def example(tmp_path):
    (tmp_path/'rtl').mkdir()
    top = tmp_path/'rtl/t_bound_top.sv'
    top.write_text('module t_bound_top; endmodule\n')
    graph=tmp_path/'asbuilt.json'; graph.write_text('{"modules":{}}\n')
    (tmp_path/'bind_report.json').write_text(json.dumps(dict(n_errors=0, errors=[], type_splits=[])))
    inv = dict(schema='opentallas.s81.bound_inventory.v1',
               source_top_sha256=hashlib.sha256(top.read_bytes()).hexdigest(),
               source_asbuilt_sha256=hashlib.sha256(graph.read_bytes()).hexdigest(),
               units={'host': dict(master='host', ports={'o': dict(dir='output',bits=[11,12])}),
                      'slice': dict(master='slice', ports={'i': dict(dir='input',bits=[21,22])})},
               drivers={'11':['host.o[0]'], '12':['host.o[1]']},
               input_pins={'21':['slice.i[0]'], '22':['slice.i[1]']})
    sinks={'slice.i[0]':['pin','host.o[0]',7,False],
           'slice.i[1]':['pin','host.o[1]',7,False]}
    (tmp_path/'bind_sinks.json').write_text(json.dumps(sinks))
    return inv, sinks


def test_actual_word_source_and_age(tmp_path):
    inv, _ = example(tmp_path)
    route = BoundDie(tmp_path, inv).route('host','o','slice','i')
    assert route['age_edges'] == 7 and route['checked_leaf_inputs'] == 2
    assert route['source_pins'] == ['host.o[0]', 'host.o[1]']


@pytest.mark.parametrize('fault', ['age', 'source', 'missing', 'ambiguous', 'stale', 'stale_graph'])
def test_wrong_current_transport_rejected(tmp_path, fault):
    inv, sinks = example(tmp_path)
    if fault == 'age': sinks['slice.i[1]'][2] = 8
    if fault == 'source': sinks['slice.i[1]'][1] = 'host.o[0]'
    if fault == 'missing': sinks.pop('slice.i[1]')
    if fault == 'ambiguous': inv['drivers']['11'].append('other.o[0]')
    if fault == 'stale': inv['source_top_sha256'] = '0'*64
    if fault == 'stale_graph': inv['source_asbuilt_sha256'] = '0'*64
    with pytest.raises(ValueError):
        BoundDie(tmp_path, inv, sinks=sinks).route('host','o','slice','i')


def test_stream_across_string_number_and_container_boundaries(tmp_path):
    obj = {'u_a.i[123]':['pin','u_b.o[456]',123456789,False],
           'quoted\\path"': {'array':[1,2,3], 'text':'x'*50}, 'number':123456789}
    p=tmp_path/'sinks.json'; p.write_text(json.dumps(obj))
    assert dict(object_items(p, chunk_size=3)) == obj
    p.write_text(p.read_text()[:-1])
    with pytest.raises(ValueError): list(object_items(p, chunk_size=3))
