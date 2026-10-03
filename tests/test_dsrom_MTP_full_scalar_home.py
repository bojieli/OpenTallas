import collections,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_MTP_full_scalar_home as M

def test_named_full_provider_not_width_only_or_fleet_adoption():
 m=M.build();i=m['instance'];c=m['cells']
 assert i['allocated_instances_this_receipt']==1 and i['physical_shard']==0
 assert i['fleet_replica_count'] is None and i['representative_parent_binding_not_proof_stage0_owns_native_MTP_program']
 assert c['full112608_protected_bits']==112608 and c['width_only_0p03135116988_NOT_ADDED']
 assert c['old_scalar_removal_or_containment_credit']==0

def test_every_native_cell_and_feedback_member_conserved():
 m=M.build();count=collections.Counter()
 for section in m['named_home']['all_cell_runs']:
  last_end=None
  for run in section['runs']:
   assert run['per_row']*run['group_width_DBU']<=1300050
   assert run['rows']==(run['count']+run['per_row']-1)//run['per_row']
   assert run['first_row_DBU']%270==0
   if last_end is not None:assert run['first_row_DBU']>=last_end
   last_end=run['first_row_DBU']+run['rows']*run['row_pitch_DBU']
   for member in run['members']:
    assert member['x_DBU']%54==0 and member['width_DBU']%54==0
    count[member['master']]+=run['count']
 assert dict(count)==m['cells']['selected_counts']
 assert count[M.ASR]==112608 and count[M.TIE]==112608

def test_full_geometry_inside_reticle_disjoint_and_area_not_fit():
 m=M.build();h=m['named_home'];b=h['bbox_DBU']
 assert b==[13313754,14925870,14639724,15995610]
 assert 0<b[0]<b[2]<=33000000 and 0<b[1]<b[3]<=26000000
 assert h['retained_rectangle_conflicts']==[] and not h['placed_fit']
 assert h['gross_mm2']>=m['cells']['gross50pct_mm2']>1.30217966172
 assert not M.overlap(b,h['reader_reservation_kept'])

@pytest.mark.parametrize('pin',['CLK','RESETN'])
def test_positive_wire_and_explicit_unproved_via_budget(pin):
 c=M.build()['clock_reset'];d=c['local_branch_loads'][pin]
 assert d['sinks']==3 and d['positive_wire_length_envelope_um']==15
 assert d['total_excluding_via_fF']<5.76 and d['remaining_to5p76_for_all_vias_fF']>0
 assert not d['actual_pin_via_route_verified']
 assert c['pin_minimum_tree_not_spatially_reachable_without_added_relays']
 assert c['first_upper8_leaf_cluster_span_um']>c['upper8_branch_wire_length_ceiling_um']

def test_local_clock_cost_and_ties_increment_not_old_credit():
 m=M.build();c=m['cells'];s=M.read('scalar_model.json');clk=m['clock_reset']
 assert c['additional_CLK_RESET_BUF_vs_pin_minimum']==51328
 assert c['selected_counts'][M.BUF]==s['cost']['cell_counts_total'][M.BUF]+51328
 assert clk['local_matched3sink_levels_per_network']==[37536,4692,587,74,10,2,1]
 assert clk['total_BUF_floor_two_networks']==85804
 assert c['gross50pct_mm2']==pytest.approx(1.32250768092)

def test_all_named_port_cuts_no_free_tracks():
 m=M.build();cuts=m['named_corridor']['cuts'];assert sum(c['signals'] for c in cuts)==384
 assert [c['signals'] for c in cuts]==[66,25,30,33,31,32,63,52,52]
 for a,b in zip(cuts,cuts[1:]):assert a['bbox_DBU'][3]<b['bbox_DBU'][1]
 for c in cuts:
  assert c['policy_half_reserved_tracks']>=c['signals']
  assert c['actual_available_after_PG_via_clock'] is None
  assert c['direction']=='HORIZONTAL' and c['layer']=='M4'

@pytest.mark.parametrize('supply,expected',[('VSS',[-9,9]),('VDD',[261,279])])
def test_literal_R0_supply_for_every_master(supply,expected):
 m=M.build();rails=m['clock_reset']['local_R0_PG_rails_DBU']
 assert set(rails)==set(m['cells']['selected_counts'])
 assert all(v[supply]==expected for v in rails.values())

def test_full_source_segment_and_unmeasured_feedback_remain_limits():
 m=M.build();l=m['latency'];a=m['admission']
 assert l['source_after_last_edges']==1026 and l['source_129280score_segment_edges']==130817
 assert l['conditional_ns_at0p9GHz']==pytest.approx(145352.22222222222)
 assert l['full_iteration_latency'] is None and not l['zero_extra_edge_measured']
 assert a['named_one_provider_cellsite_and_corridor_reservation_ready']
 assert not a['physical_G0'] and not a['RTL_GO'] and not a['rate_or_tau']
 assert not a['global_solver_changed'] and a['new_jobs']==0
