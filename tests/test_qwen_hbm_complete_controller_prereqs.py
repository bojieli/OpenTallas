"""Independent geometry controls; no actual controller execution."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_complete_controller_prereqs import model
ROOT=Path(__file__).resolve().parents[1]

def test_full_queue_epoch_and_pending_write_storage_not_free():
    r=model(ROOT);s=r['controller_extension_state']
    assert s['queue_epoch_bits']==8*32*96*32==786432
    assert s['write_pending_bits']==8*4*(16+32+34+256+64+1)==12896
    assert s['total_bits']==799384
    assert not r['hardware_build_ready'] and r['total_token_cycles'] is None
    assert r['source_defaults']['LENW']==5 and r['proposed_geometry']['LENW']==6

def test_queue_scaling_counts_each_physical_PC_and_pending_depth():
    a=model(ROOT);b=model(ROOT,qd=128,rqd=64,write_depth=8)
    assert b['controller_extension_state']['queue_epoch_bits']==2*a['controller_extension_state']['queue_epoch_bits']
    assert b['controller_extension_state']['write_pending_bits']==2*a['controller_extension_state']['write_pending_bits']

@pytest.mark.parametrize('kw',[{'qd':16},{'rqd':0},{'write_depth':0}])
def test_underprovisioned_or_infinite_missing_queue_rejects(kw):
    with pytest.raises(ValueError,match='finite queues'):model(ROOT,**kw)
