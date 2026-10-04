import gzip,json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from dsrom_s81_execution_binding import CanonicalS81Execution

def source():
    base=ROOT/'results/uarch/dsrom_native_weight_address_join_20261002'
    nodes=json.loads(gzip.decompress((base/'inputs/demand-r5.json.gz').read_bytes()))['nodes']
    bindings=[json.loads(s) for s in gzip.decompress((base/'r3/node_bindings.jsonl.gz').read_bytes()).splitlines()]
    join=object.__new__(CanonicalS81Execution)
    join.source=SimpleNamespace(nodes={n['id']:n for n in nodes},bindings={b['node']:b for b in bindings})
    return join

def test_target_chain_has_every_literal_and_fence_before_head():
    join=source()
    result=join.target_source_nodes([0,1,2],position=1048575)
    expected=tuple(n['id'] for n in join.source.nodes.values() if n['scope'] in (0,1,2,'head'))
    assert result==expected
    assert result.index('L0.fence')<result.index('L1.I0')
    assert result.index('L2.fence')<result.index('Lhead.I0')
    for p in (0,8191,1048574,True):
        with pytest.raises(ValueError):join.target_source_nodes([0],position=p)
    with pytest.raises(ValueError):join.target_source_nodes([2,1],position=1048575)
    del join.source.nodes['L1.I8']
    with pytest.raises(ValueError,match='missing/reordered'):join.target_source_nodes([1],position=1048575)

def test_literal_xu_and_gather_share_canonical_indices_not_pc_or_phase():
    join=source()
    op=join.target_native_operation('L0.I29',position=1048575,native_units=(4,))
    assert op['unit']==4 and op['output_extents']==[[41120,16]]
    assert op['index']==9+list(join.source.nodes).index('L0.I29')
    assert len(op['instruction'])==64
    assert join.target_native_operation('L0.I9',position=1048575,native_units=(6,))['output_extents']==[[51648,1280]]
    with pytest.raises(ValueError,match='provider absent'):
        join.target_native_operation('L0.I29',position=1048575,native_units=(2,5))
    with pytest.raises(ValueError,match='captured dynamic'):
        join.target_native_operation('L0.I21',position=1048575,native_units=(2,))
    with pytest.raises(ValueError,match='field dispatcher'):
        join.target_native_operation('L0.I7',position=1048575,native_units=(3,))

def test_l20_factory_census_requires_quantizers_and_later_ops_separately():
    join=source()
    required=join.target_required_bindings([20],position=1048575)
    assert len(required)==146
    assert sum(r['kind']=='instruction' for r in required)==144
    by_node={r['node']:r for r in required}
    assert [sum(r['unit']==u for r in required) for u in range(7)]==[3,9,80,30,5,2,15]
    assert by_node['L20.I20']['provider']=='qdq8-window'
    assert by_node['L20.I35']['provider']==by_node['L20.I41']['provider']=='qdq8-index'
    assert by_node['L20.I38']['provider']=='qdq4e-ckv'
    assert by_node['L20.I20']['instruction']['qe_xbase']==54720
    assert by_node['L20.I38']['instruction']['qe_xbase']==93728
    assert by_node['L20.I7']['provider']==by_node['L20.I8']['provider']=='field'
    bindings={r['node']:r['provider'] for r in required}
    assert join.require_target_bindings([20],bindings,position=1048575)==required
    del bindings['L20.I38']
    with pytest.raises(ValueError,match='missing=.*L20.I38'):
        join.require_target_bindings([20],bindings,position=1048575)
    bindings['L20.I38']='field'
    with pytest.raises(ValueError,match='wrong_provider=.*L20.I38'):
        join.require_target_bindings([20],bindings,position=1048575)
    bindings['L20.I38']='qdq4e-ckv'
    del bindings['L20.fence']
    with pytest.raises(ValueError,match='missing=.*L20.fence'):
        join.require_target_bindings([20],bindings,position=1048575)
