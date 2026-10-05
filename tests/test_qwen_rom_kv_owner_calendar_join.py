import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_rom_kv_owner_calendar_join import external_byte,home,event_dependencies,WINDOW,K_TOTAL,LAYERS
from qwen_kv_bank_prototype import k_element,v_element


@pytest.mark.parametrize('layer',[0,1,35])
def test_translation_matches_source_canonical_k_v_layout(layer):
 for head,pos,dim in [(0,0,0),(1,15,127),(1,16,0),(1,8191,127)]:
  local_k=k_element(0,head,pos,dim,kv_heads=2,position_tiles=512)
  local_v=v_element(0,head,pos,dim,v0_element=WINDOW,kv_heads=2,max_positions=8192)
  assert external_byte(layer,local_k)==k_element(layer,head,pos,dim,kv_heads=2,position_tiles=512)
  assert external_byte(layer,local_v)==v_element(layer,head,pos,dim,v0_element=K_TOTAL,kv_heads=2,max_positions=8192)


def test_homes_are_nonaliasing_and_unreserved():
 intervals=sorted((home(l,k)['logical_byte_begin'],home(l,k)['logical_byte_end_exclusive']) for l in range(LAYERS) for k in ('K','V'))
 assert intervals[0][0]==0 and intervals[-1][1]==144*1024*1024
 assert all(a[1]==b[0] for a,b in zip(intervals,intervals[1:]))
 assert not home(0,'K')['allocation_reserved']
 assert external_byte(0,17)!=external_byte(1,17)


def test_calendar_requires_real_visibility_and_reverse_retirement():
 r=event_dependencies(0);nodes={n['id']:n for n in r['nodes']}
 assert 'macro_write_visible' in nodes['local_read_permission']['requires']
 assert 'actual_backing_commit' in nodes['tail_writeback_publish']['requires']
 assert 'reverse_completion_retirement' in nodes['tail_epoch_reuse']['requires']
 assert r['timestamps'] is None and r['finite_service_cycles'] is None
 assert nodes['local_window_reuse']['requires']!=nodes['tail_epoch_reuse']['requires']


@pytest.mark.parametrize('layer,element',[(-1,0),(36,0),(0,-1),(0,2*WINDOW)])
def test_invalid_owner_address_is_rejected(layer,element):
 with pytest.raises(ValueError):external_byte(layer,element)
