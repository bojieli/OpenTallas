import sys,json,gzip
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import dsrom_c_s82_combined as C
@pytest.fixture(scope='module')
def model():return C.build()
def test_full_inventory_conserved(model):
 assert (model['weight_pairs'],model['weight_macros'],model['cfg_macros'])==(2388,9552,16716)
 assert (model['q'],model['BF'])==(1876,512)
def test_no_geometric_collision(model):
 assert not model['collisions'] and not model['out_of_die'] and not model['region_overflow']
def test_overlap_negative():
 assert C.collision_scan([{'name':'a','bbox_um':[0,0,2,2]},{'name':'b','bbox_um':[1,1,3,3]}])==[['a','b']]
def test_existing_phy_variant(model):
 assert model['PHY_stacks']==4 and model['PHY_body_mm2']==pytest.approx(40.0249506816)
 assert {a['orientation'] for a in model['rectangles'] if a['kind']=='HBM_PHY_assumed_abstract'}=={'R0','MX'}
 assert model['routing']['PHY_clock_900ps_not_833ps']
def test_every_return_storage_bit_retained(model):
 assert (model['return_bits'],model['return_nodes'],model['return_roots'])==(69771008,8064,128)
 assert model['return_mm2']==pytest.approx(52.89758742528)
def test_ragged_to_existing_return_addresses(model):
 bounds=C.P.read('stage_map')['region_bounds'];leaves=model['leaves']
 seen=[]
 for region in range(128):
  lo,hi=bounds[region:region+2]
  for slot in range(32):
   leaf=leaves[f'leaf{32*region+slot}_0']
   assert leaf['return_pair']==32*region+slot
   assert leaf['field_pair']==(lo+slot if lo+slot<hi else None)
   if leaf['active']:seen.append(leaf['field_pair'])
 assert seen==list(range(2388))
def test_inactive_return_capacity_not_credited(model):
 assert sum(v['constant_zero'] for v in model['leaves'].values())==1708*2
 assert model['complement_credit_mm2']==0
def test_native_field_width_not_replaced_by_provider_width(model):
 assert {e['bits'] for e in model['edges'] if e['class_name']=='return_binary'}=={66}
 assert {e['bits'] for e in model['edges'] if e['class_name']=='no_ready_root_capture'}=={69}
def test_no_par2_transport_ghost(model):assert model['routing']['PAR2_interdie_bits']==0
def test_power_metal_reservation_positive(model):
 assert model['PG']['total_current_A']==pytest.approx(204/.7)
 assert model['PG']['per_layer_occupancy_fraction']==pytest.approx(4/22.56)
 assert not model['PG']['macro_M7_upfeeds_qualified']
def test_actual_routed_q_failure_not_adopted(model):
 q=model['routed_q_readback'];assert q['macro_count']==4 and q['instance_count']==330898
 assert q['actual_failure']['setup_wns_ns']<0 and q['actual_failure']['hold_wns_ns']<0
 assert q['actual_failure']['drc_errors']==0
 assert q['retained_failed_abstract_not_adopted']
def test_no_phantom_capacity_or_route_admission(model):
 assert not model['full_die_fit'] and not model['hierarchical_route_admitted'] and not model['hardware_PnR_admitted']
 assert not model['rate_adopted'] and not model['PHY_inherited_containment_proven']
 assert model['unallocated_is_not_capacity_credit']
def test_canonical_screen_unchanged(model):
 assert model['retained_screen_mm2']==pytest.approx(856.5356341582075)
 assert model['retained_screen_margin_mm2']==pytest.approx(1.464365841792528)
def test_full_source_cfg_edge_inventory(model):
 assert sum(e['class_name']=='cfg_read_to_local_wordmux' for e in model['edges'])==16716
 assert model['cuts_are_static_bus_census_not_cycle_demands']
