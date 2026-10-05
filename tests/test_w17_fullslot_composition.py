import importlib.util,gzip,json
from pathlib import Path
from decimal import Decimal
import pytest
spec=importlib.util.spec_from_file_location('fullslot',Path(__file__).resolve().parents[1]/'tools/w17_fullslot_composition.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
@pytest.fixture(scope='module')
def model():return m.build()

def test_bankwise_not_aggregate_capacity(model):
    stage=model['stage_bundles'][0];b=stage['bank_slack']
    assert sum(x['physical_banks'] for x in b['spare_word_histogram'])==4*3749
    used=341*143360
    assert b['total_q_spare_physical_words']==3749*4*4096-used
    assert b['minimum_q_spare_words_per_physical_bank']==4
    assert b['spare_word_histogram'][0]==dict(words_per_bank=4,physical_banks=10880)
    assert b['total_nonexpert_fit'] is None
    with pytest.raises(ValueError,match='overflow'):
        c=json.loads(gzip.decompress(m.blob(m.PINS['residency'])));m.bank_slack(c,342)

def test_owner_reservation_not_hidden_in_BF_or_ROM_spare(model):
    owners=model['owner_placement_proposal'];assert len(owners)==40
    assert sum(s['owner_tables_per_rank'] for s in model['stage_bundles'])==40
    assert all(x['physical_coordinates'] is None and x['actual_nonexpert_hub_stage'] is None for x in owners)
    t=model['owner_space_test'];assert not t['owner_fits_one_conditional_BF_spare_under_candidate_register_realization']
    assert Decimal(t['deficit_um2'])==Decimal('3984.52186')
    assert model['no_double_count']['owner_tables_not_weight_bank_capacity']

def test_reference_arithmetic_cannot_qualify_complete_product(model):
    assert model['expert_only_stage_count']==46 and model['product_stage_count'] is None
    assert not model['old_45_stage_capacity_credit']
    assert not model['q_template_composition']['old_outline_fit_transferred']
    assert model['mapped_BF_baseline']['spatial_clock_verdict']=='DIRECT_STACK_HYPOTHESIS_REFUTED_PHYSICAL_HOLD'
    assert all(s['full_slot_fit'] is None and s['dense_HC_addition_mm2'] is None for s in model['stage_bundles'])
    assert not model['physical_admission'] and not model['engine_RTL_build_ready']
    assert model['full_token_rate'] is None
