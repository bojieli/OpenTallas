import hashlib,json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import uarch_model_qwen_launch_producer as M


def test_same_corner_source_arrivals_expose_nominal_setup_failure():
 r=M.price()
 assert r['status']=='FAIL_NOMINAL_SOURCE_PRODUCER_SETUP_CONTEXT'
 assert r['worst_SS_setup_slack_ps']==pytest.approx(-27.37327,abs=.001)
 assert r['worst_FF_hold_violation_ps']==0
 for p in r['producer_instances']:
  a=r['corners']['ss'][p]['transitions']['rise']
  assert a['arrival_minmax_after_producer_clock_ps'][1]>126
  assert all(c['nominal_same_phase_hold_setup_slack_ps'][1]<0 for c in a['constraints'])


def test_uses_allocated_cells_loaded_real_pins_and_both_nonzero_wires():
 r=M.price()
 assert r['producer_instances']=={'joined_ready[0]':'B','held_valid[0]':'A'}
 for rows in r['corners'].values():
  for row in rows.values():
   assert row['local_wire_RC_ps']>0
   assert row['source_allocation']['domain']=='stream'
   assert row['source_allocation']['restoring_cell']=='INVx1_ASAP7_75t_R'
   assert row['QN_cap_fF']>2*.165790 and row['INV_cap_fF']>2*.165790
 assert r['explicit_local_QN_to_INV_wire_um']==r['explicit_local_INV_to_AND_wire_um']==2


def test_unbound_route_phase_and_no_double_area_or_clock_relaxation():
 r=M.price();c=r['model_charge']
 assert r['actual_hub_to_provider_route_um'] is None and r['source_clock_phase_vs_provider_unbound']
 assert c['already_in_owned_ready_1201_FFs'] and c['FF_and_INV_cells_added']==c['new_cycles']==0
 assert c['payload_bits_per_issue']==507 and c['control_boundary_bits']==2
 assert not any(r[k] for k in ('physical_source_admission','default_enabled','RTL_changed','new_map','new_token'))
 assert r['SS_setup_uncertainty_ps']==60 and r['FF_hold_uncertainty_ps']==25
 assert r['clock_period_ps']==pytest.approx(833.33333333)
 assert r['necessary_common_producer_minus_provider_clock_phase_ps'][1]<-27


def test_current_pins_and_archived_model_cold_replay():
 r=M.price()
 for p,h in r['source_sha256'].items():assert hashlib.sha256((M.ROOT/p).read_bytes()).hexdigest()==h,p
 expected=json.loads((M.ROOT/M.OUT/'model-r2.json').read_text())
 assert json.loads(json.dumps(r))==expected
