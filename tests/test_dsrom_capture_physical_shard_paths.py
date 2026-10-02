import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_physical_shard_paths as P

def test_seats_roots_and_order():
 m=P.build()
 assert len(m['ordered_rows'])==576
 assert [sum(r['physical_shard']==s for r in m['ordered_rows']) for s in (0,1)]==[320,256]
 assert m['ordered_output']==list(range(576))
 for r in m['ordered_rows']:
  assert r['physical_shard']*64+r['local_root']==r['logical_root']
 assert m['single_logical_phase_lease']

def test_distinct_remote_path_and_no_free_geometry():
 m=P.build()
 assert not m['paths'][0]['requires_physical_stage_boundary']
 assert m['paths'][1]['requires_physical_stage_boundary']
 assert m['remote_rows_per_phase']==256
 assert m['full_phase_latency_delta_cycles'] is None
 assert not m['contextual_PR_admitted']
 assert m['frozen_global_context_bits']==169
 assert m['routed_context_bits']==170
 assert m['physical_shard_is_separate_route_field']
 assert m['phase_context_bits']==170
 assert m['request_bits']==187 and m['reply_bits']==240

@pytest.mark.parametrize('row',[-1,576,True,1.5])
def test_invalid_row_rejected(row):
 with pytest.raises(ValueError):P.owner(row)

def test_local_root_alias_does_not_alias_die():
 assert P.owner(0)['local_root']==P.owner(128)['local_root']==0
 assert P.owner(0)['physical_shard']!=P.owner(128)['physical_shard']

def test_rectangle_envelope_not_route_bound():
 d=P.rect_distance([0,0,1000,1000],[3000,4000,5000,6000])
 assert d['endpoint_L1_min_um']==5
 assert d['endpoint_L1_max_um']==11
 assert d['actual_pin_route_length_um'] is None
