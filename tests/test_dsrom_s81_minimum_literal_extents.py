from pathlib import Path
import gzip,json,sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from dsrom_s81_execution_binding import minimum_vm_extents

def test_actual_literal_forward_and_head_extents():
    raw=ROOT/'results/uarch/dsrom_native_weight_address_join_20261002/inputs/demand-r5.json.gz'
    nodes={n['id']:n for n in json.loads(gzip.decompress(raw.read_bytes()))['nodes']}
    for node,ranges in [('L0.I29',[[41120,16]]),('L0.I8',[[420096,128]]),
                        ('L0.I9',[[51648,1280]]),('L0.I10',[[54208,512]]),
                        ('Lhead.I2',[[41344,5120],[51584,1]])]:
        assert minimum_vm_extents(nodes[node]['instruction'])==ranges
    with pytest.raises(ValueError,match='captured dynamic'):
        minimum_vm_extents(nodes['L0.I21']['instruction'])

def test_dynamic_bounds_and_duplicate_strobes_are_not_coalesced():
    op=dict(unit=2,su_nout=1,su_nin=4,dst=1,o_d='WINM1',o_si=1)
    assert minimum_vm_extents(op,dynamic={'WINM1':10})==[[10,4]]
    with pytest.raises(ValueError):minimum_vm_extents(op,dynamic={'WINM1':(1<<19)-2})
    with pytest.raises(ValueError):minimum_vm_extents(dict(op,o_si=0),dynamic={'WINM1':10})
    with pytest.raises(ValueError,match='provider required'):
        minimum_vm_extents(dict(unit=4,xu_op=2))
