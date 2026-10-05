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


def test_refill_bandwidth_or_watchdog_never_qualifies_service():
    r=build();w=r['WINDOW_refill']
    assert w['mandatory'] and w['actual_run_source_receipt']['commit'].startswith('d2cabe7ce')
    assert w['actual_source_backend']['CLK_PS']==1000
    assert w['actual_source_fixture']['WINDOW_REFILL_CREDITS']==1
    assert w['warm_descriptor_requires_cold_refill']
    assert len(w['conditional_scalar_replay_cases'])==26
    assert w['actual_measured_runtime_refill_cycles'] is None
    assert w['actual_PC24_request_response_refresh_stall_counters'] is None
    assert w['cold_refill_absolute_dependency_calendar'] is None
    assert w['warm_retention_image_user_row_epoch_reset_lifetime'] is None
    assert not w['nominal_stack_bandwidth_substitution_permitted']
    for key in ('WINDOW_refill_actual_backend_clock_and_refresh_bound',
                'WINDOW_finite_outstanding_and_response_credit_calendar',
                'WINDOW_backend_completion_visibility_before_attention',
                'WINDOW_cold_init_and_warm_retention_identity_lifetime_schedule'):
        assert r['obligation_gates'][key] is False
    assert not r['hardware_admission'] and r['full_token_cycles'] is None
