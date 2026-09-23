import pytest
from tools.audit_v41_rom_service_ownership import ownership


def test_cold_banks_do_not_supply_selected_shards():
    r=ownership(20,39,4,72)
    assert r['resident_expert_shards_per_chip']==780
    assert r['pooling_advantage_factor']==780
    assert r['fully_pooled_expert_read_us']==pytest.approx(2.6112)
    assert r['uniform_fixed_bank_expert_read_us']==pytest.approx(2036.736)


def test_selection_does_not_shorten_uniform_bank_sweep():
    a,b=ownership(20,39,4,72,1),ownership(20,39,4,72,6)
    assert a['uniform_fixed_bank_expert_read_us']==b['uniform_fixed_bank_expert_read_us']
    assert b['fully_pooled_expert_read_us']==6*a['fully_pooled_expert_read_us']
    assert b['fixed_bank_active_TB_s']==pytest.approx(6*a['fixed_bank_active_TB_s'])


def test_no_cold_bank_case_matches_pooled_service():
    r=ownership(1,1,4,72)
    assert r['fully_pooled_expert_read_us']==r['uniform_fixed_bank_expert_read_us']
