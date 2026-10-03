import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_s82_native_return as M
@pytest.fixture(scope='module')
def d():return M.build()
def test_full_D64_native_count(d):
 a=d['actual_mapping'];assert a['cells']==77952 and a['flops']==9143
 assert a['ports']==16 and a['port_bits']==202
def test_complete_node_exceeds_storage_only_slot(d):
 assert d['node_FF50_projection_mm2']==pytest.approx(129.0200389632)
 assert d['node_logic_delta_before_containment_mm2']==pytest.approx(77.74969337856)
def test_native_only_mapper():
 with pytest.raises(ValueError,match='non-native'):
  M.summarize({'modules':{'ot_v41_retn_w17w10':{'cells':{'fake':{'type':'$_MUX_'}},'ports':{}}}})
def test_no_unused_root_or_capacity_credit(d):
 assert d['native_node_instances']==8064 and d['root_instances_retained']==128
 assert d['root_storage_retained_mm2']==pytest.approx(1.62724184064)
def test_area_mapping_not_PnR_or_universal_impossibility(d):
 assert d['one_explicit_NAND_INV_construction_not_minimum_area_proof']
 assert not d['SSFF_timing_qualified'] and not d['PnR_admitted'] and not d['full_die_fit']
 assert not d['capacity_impossibility_claim'] and not d['root_logic_mapped']
