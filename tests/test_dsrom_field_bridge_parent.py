import sys,json,collections,copy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_field_bridge_queue_bounds as Q
import dsrom_field_bridge_parent as P
O=(0,0,0,10,2149580800,0,0,0,66,0)

def ready(rows=2):
 b=P.PhaseBridge(rows,1,O);b.reserve(b.depth,True,True);b.launch();return b

def test_actual_replay_equals_retained_roots_and_visible():
 a=Q.actual_certificate();r=a['queue_recurrence']
 assert a['status'].startswith('PASS') and r['predicted_retired_rows']==576
 assert r['peak_node_queues_per_level']==[2,1,2,2,1,1]
 assert r['peak_root_input']==1 and r['peak_root_held']==0
 assert not r['node_faults'] and not r['root_faults'] and r['all_queue_and_held_debt_drained']
 assert not a['actual_node_occupancy_observed'] and not a['full_program_internal_bound']

def test_leaf_duplicate_cannot_get_count_credit():
 leaf=(394,42,(0,0,0,0,1))
 with pytest.raises(ValueError):Q.replay([leaf,leaf])

def test_source_tag_width_unpack():
 t=(3<<29)|(575<<13)|(2<<8)|(1<<5)|3
 assert Q.unpack(t)==(3,575,2,1,3)

def test_static_no_service_credit_and_six_inconclusive():
 m={'rows':8192,'plans':[[0,g,g//32,32,128,0,32] for g in range(0,4096,32)]}
 # Each plan yields32rows perMB and source ownership agrees, leaves perroot64.
 one=Q.static_phase_bound(m,1);six=Q.static_phase_bound(m,6)
 assert one['pass_node64_root128_held128'] and one['max_total_raw_partials_to_root']==64
 assert not six['pass_node64_root128_held128']
 assert six['max_total_raw_partials_to_root']==384

@pytest.mark.parametrize('exclusive,reset',[(False,True),(True,False)])
def test_no_launch_without_writer_or_reset_lease(exclusive,reset):
 b=P.PhaseBridge(576,1,O)
 with pytest.raises(ValueError):b.reserve(b.depth,exclusive,reset)
 with pytest.raises(ValueError):b.launch()

def test_phase_capacity_is_576_not_6x8192():
 b=ready(576);assert sum(b.depth)==576 and [sum(b.depth[:64]),sum(b.depth[64:])]==[320,256]
 with pytest.raises(ValueError):b.reserve(b.depth,True,True)

def test_finite_installed_capacity_cannot_hide_W2():
 b=P.PhaseBridge(1280,1,O);assert sum(b.depth)==1280
 with pytest.raises(ValueError):b.reserve([4]*128,True,True)

def test_same_owner_visible_then_positive_credit_and_preF():
 b=ready();b.capture(10,O,0,0,0,0,1);b.capture(10,O,0,0,1,0,2)
 for row in (0,1):
  with pytest.raises(ValueError):b.vm_visible(10,O,0,row,True,True)
  with pytest.raises(ValueError):b.vm_visible(11,O,0,row,False,True)
  b.vm_visible(11,O,0,row,True,True)
  with pytest.raises(ValueError):b.credit_return(11,O,0,row)
  b.credit_return(12,O,0,row)
 with pytest.raises(ValueError):b.rearm(12,True,0)
 with pytest.raises(ValueError):b.rearm(13,True,1)
 assert b.rearm(13,True,0)==13 and b.vmlease
 with pytest.raises(ValueError):b.release_vmlease(False)
 b.release_vmlease(True);assert not b.vmlease

@pytest.mark.parametrize('which',[5,6,7,9])
def test_wrong_generation_user_version_reset_cannot_retire(which):
 b=ready();b.capture(10,O,0,0,0,0,1);bad=list(O);bad[which]+=1
 with pytest.raises(ValueError):b.vm_visible(11,bad,0,0,True,True)
 assert not b.visible and (0,0) in b.records

def test_wrong_shard_and_duplicate_does_not_clear_capture():
 b=ready()
 with pytest.raises(ValueError):b.capture(10,O,1,0,0,0,1)
 b.capture(10,O,0,0,0,0,1)
 with pytest.raises(ValueError):b.capture(11,O,0,0,0,0,1)
 assert len(b.records)==1

def test_reset_cannot_erase_accepted_debt():
 b=ready();b.capture(10,O,0,0,0,0,1)
 with pytest.raises(ValueError):b.reset(1,True)
 assert b.go and len(b.records)==1

def test_packet_timeout_original_failure_retained():
 p=P.packet_service(765,timeout=1024)
 assert p['packets'][0]['flits']==256 and not p['all_timeout_PASS']
 assert P.packet_service(765,timeout=4096)['all_timeout_PASS']

@pytest.mark.parametrize('n',[1,256,765,766,4096])
def test_packet_finite_records_counts(n):
 p=P.packet_service(n)
 assert sum(x['rows'] for x in p['packets'])==n
 assert all(x['flits']<=256 and x['occupied_cycles']>x['rows'] for x in p['packets'])
 assert p['cycles']==sum(x['occupied_cycles'] for x in p['packets'])

def test_single_owner_identity_fields_never_truncated():
 bad=list(O);bad[6]=1<<32
 with pytest.raises(ValueError):P.PhaseBridge(576,1,bad)

def test_all_compiled_phase_count_certificate():
 x=json.loads((Q.OUT/'queue_model.json').read_text())['all_compiled']
 assert x['counts']=={'phases':46509,'singleposition_count_certificate_PASS':46509,'sixposition_count_certificate_PASS':46419}
 assert x['singleposition_max_node_side_writes_per_level']==[3,6,12,24,48,64]
 assert x['singleposition_max_root_raw_writes']==64

def test_model_does_not_admit_failed_readcut_or_free_routes():
 x=json.loads((Q.OUT/'model.json').read_text())
 assert not x['engine_RTL_admitted'] and not x['physical_fit'] and not x['rate_adopted']
 assert x['ports']['capture_read_pipeline_cycles']==13
 assert x['cost_floor']['existing_capture_replacement_credit']==0
 assert x['route_selection']['actual_legal_boundary_pins_and_routes'] is None
 assert x['prospective_I66']['VM_addresslease_still_held']
 assert x['prospective_I66']['actual_wholeprogram_criticalpath_delta'] is None

def test_blocked_read_sink_cannot_overflow_or_stall_native_field():
 t=P.ReadTokens(O)
 for i in range(16):t.issue(i,i)
 with pytest.raises(ValueError):t.issue(16,16)
 with pytest.raises(ValueError):t.transfer(20,0,O,False,True)
 t.transfer(20,0,O,True,True)
 with pytest.raises(ValueError):t.return_credit(20,0,O)
 t.return_credit(21,0,O)
 with pytest.raises(ValueError):t.issue(21,16)
 t.issue(22,16)
 assert len(t.pending)==16

def test_early_or_stale_readreturn_retains_matching_debt():
 t=P.ReadTokens(O);t.issue(10,7)
 with pytest.raises(ValueError):t.transfer(22,7,O,True,True)
 bad=list(O);bad[5]=1
 with pytest.raises(ValueError):t.transfer(23,7,bad,True,True)
 assert t.pending[7]==(10,None)
