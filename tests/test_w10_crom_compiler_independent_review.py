"""Keep canonical replay distinct from refuted original catalog admission."""
import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'results/quality/w10_crom_compiler_independent_review_20261001/reproduce.py'
@pytest.fixture(scope='module')
def review():
    spec=importlib.util.spec_from_file_location('independent_crom_review',PATH)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.build()

def test_canonical_all_source_addresses_and_both_axes(review):
    assert review['canonical_catalog_counts']['commands_per_rank']==491
    assert review['persisted_all_address_mask_operand_roundtrip_uses']==549760
    assert sum(review['uses_by_axis'].values())==549760
    assert len(review['independent_operand_axes'])>=2
    assert review['all_four_encoded_rank_metadata_match']

def test_original_verifier_negative_metadata_controls_preserved(review):
    failures={m['mutation']:m['original_verifier_accepted_uses'] for m in review['original_verifier_counterexamples']}
    assert failures==dict(predicate=549760,empty_commands=0,encoded_source_hash=549760,declared_command_count=549760)
    assert not review['persisted_verifier_source_complete']
    assert not review['compiled_6c7_join_qualified']

def test_local_geometry_and_unpriced_qualification_stay_rejected(review):
    assert review['local_geometry_replay_equal']
    assert review['local_route_each_direction_fast_cycles']==11
    assert review['placement_verdict']=='REJECT_UNRESERVED_SU_DISPLACEMENT'
    for row in review['local_scenarios']:
        assert row['added_forward_control_pipeline_bits']==704
        assert row['added_reverse_control_pipeline_bits']==768
        assert row['old75route_power_not_subtracted']
        assert not row['ungated_added_control_clock_and_data_reservation_bound']
    assert review['full_operator_latency'] is None
    assert not review['hardware_admission'] and review['headline_rate'] is None
