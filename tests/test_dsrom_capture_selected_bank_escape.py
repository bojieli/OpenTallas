import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_selected_bank_escape as B
@pytest.fixture(scope='module')
def model():return B.build()
def test_only_selected_bank(model):
 assert model['single_bank'] and model['unselected_annex_charge_mm2']==0
 assert model['bank']['cells']==70406
 assert model['selected_bank_bbox_DBU']==[3129786,8953200,3147930,9745920]
def test_literal_supply_and_escape_debt(model):
 assert model['bank']['literal_supply_shapes_covered']==140812
 assert model['bank']['signal_ports_requiring_named_escape']==140812
 for x in [model['bank']]+model['raw']:
  assert x['M1_supply_contact_union'] and not x['signal_pin_supply_overlap']
  assert not x['external_PG_feed_via_or_signal_escape_proven']
def test_no_common_deficit_transfer(model):
 assert model['common_colocation_counterfactual_deficit_mm2']>0
 assert model['selected_raw_rows_eliminate_this_colocation_requirement']
 assert model['remaining_proven_global_fit_deficit_mm2'] is None
 assert model['island_lower_area_remaining_before_tokens_ingress_routes_mm2']>0
 assert not model['contextual_PR_admitted'] and not model['physical_fit']
def test_supply_removal_rejected():
 lef='  PIN VDD\n RECT 0 0.261 0.378 0.279;\n  END VDD\n  PIN VSS\n RECT 0 -0.009 0.378 0.009;\n  END VSS\n  PIN A\n RECT 0.018 0.126 0.073 0.144;\n  END A\n  PIN Y\n RECT 0.145 0.225 0.357 0.243;\n  END Y'
 with pytest.raises(ValueError,match='supply gap'):B.audit([{'bbox_DBU':[0,0,378,270],'orientation':'R0'}],[],lef)
