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
