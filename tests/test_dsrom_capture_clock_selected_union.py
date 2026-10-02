import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_clock_selected_union as J

def test_single_bank_and_actual756_load_violations():
 m=J.build();b=m['selected_selector_clock_construction']
 assert b['named_bank_bbox_DBU']==[3129786,8953200,3147930,9745920]
 assert b['core_clock70406']==70406 and b['spare_sites']==58
 assert m['prior51ae_annex_charge_mm2']==0
 assert sum(c['source_lower_bound_5p76_violations'] for c in m['per_shard_raw_clock_correction_proposals'])==756
 assert m['positive_new_relay_and_pad_BUF']==68614
 assert m['common_if_all_correction_colocated_deficit_mm2']>0
 assert not m['physical_fit'] and not m['contextual_PR_admitted']

def test_positive_buffer_costs_and_reserved_contact_cap():
 m=J.build()
 for c in m['per_shard_raw_clock_correction_proposals']:
  assert c['additional_relay_BUF']>0 and c['additional_equal_cell_depth_pad_BUF']>0
  assert c['proposed_metal_budget_fF']+c['remaining_contacts_stubs_coupling_budget_fF']==5.76
  assert not c['contact_capacitance_proven']
 assert m['raw_clock_50pct_additional_reserve_mm2']>0
 assert m['user_identity_bits']==32
 assert m['typed_direct_HQ_INV_HQ_forward_BUF_lowerbound']==3
 assert m['typed_samecell_feedback_BUF_lowerbound']==2
 assert m['actual_consumer_deadline'] is None

def test_no_fanout_relaxation():
 net={'source':{'instance':'a','point_DBU':[0,0]},'name':'a.Y','sinks':[{'instance':str(i),'pin':'CLK','point_DBU':[1000,0]} for i in range(9)],'source_wire_allowance_5p76_fF_exceeded_in_this_route_family':False}
 with pytest.raises(ValueError):J.correction([net],{'M8':.1,'M9':.09})


def test_existing_emptyrow_disjoint_sites_with_literal_supplies():
 m=J.build()
 for inv in m['raw_empty_row_correction_site_inventories']:
  assert inv['literal_new_VDD_VSS_in_same_net_M1_rail_union']
  assert inv['remaining_free_sites']>0
  assert len(inv['proposed_sites'])==inv['requested_sites']
  assert len({s['proposed_site_ID'] for s in inv['proposed_sites']})==inv['requested_sites']
  assert all(s['orientation']=='MX' and s['actual_instance_net_assignment'] is None for s in inv['proposed_sites'])
