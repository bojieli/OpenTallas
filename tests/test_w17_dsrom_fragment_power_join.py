import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w17_dsrom_fragment_power_join as J

def test_fresh_power_inventory_and_identity_do_not_transfer_admission():
    r=J.build()
    assert r['state']['additional_fragment_FF_bits']==192*24928*318
    assert r['state']['all_ungated_FF_bits']==3595629118
    assert r['identity_admission']['required_model_epoch_bits']==32
    assert r['identity_admission']['candidate_epoch_bits']==8
    assert not r['identity_admission']['fresh_typed_epoch8_power_applies_to_epoch32_candidate']
    assert not r['conditional_power']['serialized_selected_data_bound']
    assert r['conditional_service']['maximum_local_row_cycles']==2360
    assert not r['physical_admission'] and r['full_token_latency'] is None
