import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from w13_index_finite_trace import trace_decode

def test_bounded_actual_produced_bits_replay_and_source_output():
 d=trace_decode();assert d['source_rows']==['normal','negative_zero']
 assert d['real_key_rows']==2 and d['interpreter_padded_lanes']==30
 assert d['checkpoint_reads']==0 and not d['physical_admission']
 for b in d['blocks']:
  assert b['unmodified_source_output_equal']
  assert len(b['executed_instruction_events'])==810
  assert b['physical_register_allocation'] is None

def test_executed_lane_branches_and_exact_operand_versions():
 d=trace_decode()
 for b in d['blocks']:
  events=b['executed_instruction_events'];results={}
  for e in events:
   assert e['RF_read_tick'] is None and e['writeback_tick'] is None
   for o in e['operands']:
    for producer in o['producer_result_ids']:
     assert producer>=0 and producer<e['id'] and producer in results
    if o['producer_result_ids']:
     assert len(o['producer_result_ids_by_active_lane'])==len(e['active_lane_indices'])
   if 'result_id' in e:results[e['result_id']]=e['result_value_sha256']
   if e['branch_decision'] is not None:
    a=e['branch_decision'];assert set(a['yes_lanes']).isdisjoint(a['no_lanes'])
    assert set(a['yes_lanes'])|set(a['no_lanes'])==set(e['active_lane_indices'])
