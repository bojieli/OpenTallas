import pytest
from tools.w17_dsrom_sync_whole_gate import build,gamma_delivery_gate

def test_legacy_fast_gamma_rejected():
    with pytest.raises(ValueError):gamma_delivery_gate(5120,319)
    with pytest.raises(ValueError):gamma_delivery_gate(5120,38)
    assert gamma_delivery_gate(5120,320)

def test_incomplete_inventory_has_no_positive_margin():
    r=build()
    assert r['candidate']['register_reservation']==4378995838
    assert r['candidate']['branch_NAND2_equivalent_reservation']==20444736
    assert r['power']['complete_margin_W'] is None
    assert not any(r['obligation_gates'].values())
    assert r['admission_verdict']=='FAIL_INCOMPLETE_WHOLE_POINT'
    assert not r['hardware_admission']
