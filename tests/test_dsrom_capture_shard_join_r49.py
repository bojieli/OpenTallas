import json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from dsrom_capture_shard_join_r49 import model,identity
@pytest.fixture(scope='module')
def m():return model()
def test_actual_768_source_maps_split_seats(m):
 assert m['verified_source_matrices']==768
 assert [s['seats'] for s in m['shards']]==[320,256]
 assert [sum(s['depths_by_local_root'].values()) for s in m['shards']]==[320,256]
 assert len({r['row'] for s in m['shards'] for r in s['ordered_owned_rows']})==576
 assert m['shards'][0]['depths_by_local_root'][0]==6 and m['shards'][1]['depths_by_local_root'][0]==4
@pytest.mark.parametrize('row,shard,root',[(0,0,0),(128,1,64),(255,1,127),(256,0,0),(511,1,127),(575,0,31)])
def test_owner_shard_not_stage_or_rank(row,shard,root):
 assert identity(row,57,3,shard)['logical_root']==root
 with pytest.raises(ValueError):identity(row,57,3,1-shard)
def test_width_and_rawslot_feedback_price(m):
 assert (m['context_bits'],m['request_bits'],m['reply_bits'])==(170,187,240)
 assert m['feedback']['raw_BUFs']+m['feedback']['control_BUFs']==82454
 assert abs(m['feedback']['slot_delta_um2']-2*576*69*.10206/.5)<1e-8
 assert [s['raw69_slot']['width_um'] for s in m['shards']]==[204.93]*2
 assert all(not s['raw69_slot']['control_read_clock_PG_included'] for s in m['shards'])
def test_routes_deadlines_and_capacity_remain_unselected(m):
 assert m['no_combinational_read_tree_across_dies'] and m['logical_phase_lease_count']==1
 assert m['offdie_service']['return_gather_home'] is None and m['finite_token_capacity'] is None
 assert not m['registered_stage_cuts_selected'] and not m['physical_admitted']
 assert m['ordered_global_output_rows']==list(range(576))
