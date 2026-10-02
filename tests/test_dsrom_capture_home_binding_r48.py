import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from dsrom_capture_home_binding_r48 import model,gap

def test_inventory_preserves_source_map():
 m=model();assert len(m['root_envelopes'])==64 and m['total_capture_seats']==576 and m['raw_record_bits']==69
 assert len({i for r in m['root_envelopes'] for i in r['source_pair_ids']})==2048

def test_box_gap_not_actual_route():
 assert gap([0,0,10,10],[15,20,30,30])==15
 m=model();assert all(r['routed_distance'] is None and r['root_output_pin'] is None and r['capture_bank_home'] is None for r in m['root_envelopes'])
 assert min(r['minimum_frame_to_reserved_service_gap_DBU']['HUB_VM'] for r in m['root_envelopes'])>0

def test_domain_and_unknown_deadline_failclosed():
 m=model();assert m['source_clock_contract']['stream_period_ps']==1000/1.2
 assert m['source_clock_contract']['serial_period_ps']==1000/.9
 assert m['actual_consumer_deadline'] is None and m['CDC_latency_edges'] is None
 assert not m['registered_stage_cuts_selected'] and not m['physical_admitted']

def test_parent_feedback_scope_not_forward_credit():
 p=model()['parent_private_design'];assert p['feedback_only_BUFx4_count']==82454
 assert abs(82454*.10206-p['feedback_only_body_um2'])<1e-8
 assert not p['typed_feedback_cone_reproduced'] and p['forward_hold_screen'] is None
 assert (p['request_bits'],p['reply_bits'])==(169+1+16,169+69+1)
