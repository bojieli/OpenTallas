"""Exact synchronous candidate admission gate; incomplete power has no margin."""
import argparse,hashlib,json,subprocess
from decimal import Decimal

def gamma_delivery_gate(words,cycles,ports=16):
    if words<0 or cycles<0 or ports!=16 or cycles*ports<words:
        raise ValueError('gamma schedule exceeds16 selected FP32 outputs/fast cycle')
    return True

def build():
    pins={}
    def load(name,ref,path):
        b=subprocess.check_output(['git','show',ref+':'+path])
        pins[name]=dict(commit=subprocess.check_output(['git','rev-parse',ref]).decode().strip(),path=path,sha256=hashlib.sha256(b).hexdigest())
        return json.loads(b)
    window=load('actual_L0_WINDOW_source_receipt','d2cabe7ce','results/rtl/w17_connected_token_preparation_20261001/L0_PC24_actual_HBM_service_binding.json')
    scalar=load('conditional_WINDOW_scalar_receipt','d2cabe7ce','results/rtl/w17_connected_token_preparation_20261001/L0_PC24_window_service_scalar.json')
    for path,expected in window['source_sha256'].items():
        source=subprocess.check_output(['git','show',window['source_commit']+':'+path])
        if hashlib.sha256(source).hexdigest()!=expected:
            raise ValueError('WINDOW actual source receipt mismatch: '+path)
    code=subprocess.check_output(['git','show','d2cabe7ce:tools/w17_L0_window_service_expectation.py'])
    if hashlib.sha256(code).hexdigest()!=window['conditional_expectation']['tool_sha256']:
        raise ValueError('WINDOW scalar tool source mismatch')
    env={'__name__':'pinned_conditional_replay'};exec(compile(code,'<pinned WINDOW scalar>','exec'),env)
    cases=[env['replay'](c,3,e) for e in (1,2) for c in range(12200,13401,100)]
    if cases!=scalar['cases']:
        raise ValueError('WINDOW conditional scalar replay mismatch')
    b=load('sync_branch','5b8c456a','results/quality/w16_engram_rom_constructive_home_20261001/sync_branch_drain_inventory.json')
    c=load('frozen_CROM','2a4980765','results/quality/w16_engram_initializer_20261001/frozen_closure.json')
    typed=load('typed_partial_power','2b14a8e56','results/uarch/w10_engram_sync_drain_power_r1/budget.json')
    assert typed['conditional_total_FF_bits']==4378995838 and typed['additional_branch_NAND2_cells']==20444736
    assert not typed['complete_inventory'] and not typed['actual_power_qualified']
    storage=b['control_storage'];gate=b['synchronous_branch']
    assert storage['per_home_total']==sum(storage['per_home_roles'].values())==91170
    assert storage['conditional_total_register_bits']==storage['prior_all_E32_FF_preserved']+192*91170==4378995838
    assert gate['conditional_branch_NAND2_equivalent_total']==192*8191*13==20444736
    gamma_delivery_gate(5120,320)
    obligations={k:False for k in ['all_localidle_enables_reset_compare_serializer_gates',
        'selected_control_dynamic_activity_and_capacitance','all_register_and_macro_clock_and_leak',
        'selected_data_switching','actual_branch_payload_fanout_buffers',
        'all_control_register_gate_capture_and_macro_physical_slots',
        'actual_interdie_and_serial_CDC','reset_retention_and_full_consumer_drain',
        'contextual_SS_setup_FF_hold','complete_valid_frozen_image_and_encoded_bases',
        'CROM_finite_selected_port_deadlines_and_whole_calendar',
        'WINDOW_refill_actual_backend_clock_and_refresh_bound',
        'WINDOW_finite_outstanding_and_response_credit_calendar',
        'WINDOW_backend_completion_visibility_before_attention',
        'WINDOW_cold_init_and_warm_retention_identity_lifetime_schedule']}
    assert not b['exact_all_control_storage'] and not c['complete_frozen_image']
    return dict(schema='opentallas.DSROM-synchronous-whole-admission.v1',source_pins=pins,
        candidate=dict(homes=192,table_macros=1500067,
            register_reservation=storage['conditional_total_register_bits'],
            incremental_register_roles_per_home=storage['per_home_roles'],
            branch_NAND2_equivalent_reservation=gate['conditional_branch_NAND2_equivalent_total'],
            synchronous_internal_hops=True,async_mailboxes_per_internal_hop=False,
            reservation_not_minimum=True,actual_complete_inventory=False),
        power=dict(typed_partial_ledger_bound=True,typed_inventory_complete=False,
            typed_partial_max_home_clock_and_all_leak_W=max(typed['homes'],key=lambda h:Decimal(h['clock_plus_all_leak_W']))['clock_plus_all_leak_W'],
            typed_branch_dynamic_is_all_activity_allocation_not_selected=True,
            complete_selected_phase_W=None,complete_margin_W=None,
            provisional_positive_margin_permitted=False,old_3e66_e851_power_currency=False,
            clock_data_control_dynamic_all_required=True),
        physical_slots=dict(actual_all_added_register_gate_buffer_placement=None,
            historical_macro_rectangle_screen_not_added_control_fit=True),
        CROM=dict(logical_words=549760,L1_invalid_hole=[508800,529280],
            selected_FP32_ports=16,gamma5120_minimum_fast_cycles=320,
            gamma414720_minimum_fast_cycles=25920,
            legacy_faster_delivery_assumptions_usable=False,complete_image=False),
        WINDOW_refill=dict(mandatory=True,actual_run_source_receipt=pins['actual_L0_WINDOW_source_receipt'],
            source_profile_scope='pinned L0 runtime only; no automatic all40/head provider transfer',
            source_receipt_verified_file_count=len(window['source_sha256']),
            actual_source_backend=window['actual_backend'],
            actual_source_fixture=window['fixture'],
            conditional_scalar_replay_cases=cases,
            conditional_scalar_scope=scalar['scope'],
            watchdog_risk=window['watchdog_risk'],
            actual_measured_runtime_refill_cycles=None,
            warm_retention_disabled_for_audited_L0=True,
            warm_descriptor_requires_cold_refill=True,
            actual_backend_clock_parameter_forwarding_and_effective_CLK_PS=None,
            actual_refresh_timing_bank_policy_and_interference=None,
            actual_request_outstanding_and_return_credit_limits=None,
            actual_consumer_completion_visibility_and_order=None,
            actual_PC24_request_response_refresh_stall_counters=None,
            cold_refill_absolute_dependency_calendar=None,
            warm_retention_image_user_row_epoch_reset_lifetime=None,
            actual_warm_or_cold_token_cycles=None,
            nominal_stack_bandwidth_substitution_permitted=False,
            unmeasured_source_prediction_is_not_runtime_counter=True,
            watchdog_limit_not_service_completion_measurement=True,
            active_run_preserved=True,owner='Godel',
            qualification='UNBOUND_MANDATORY_REFILL_SERVICE'),
        obligation_gates=obligations,admission_verdict='FAIL_INCOMPLETE_WHOLE_POINT',
        hardware_admission=False,full_token_cycles=None,
        owner_actions=dict(Avicenna='complete actual control/state/branch/reset/drain and boundary instance inventory',
            Confucius='fresh typed clock/leak/control+data phase power with actual activity and load; no margin until complete',
            Fermat='publish source-valid padded image and encoded bases; L1 absent remains hard gate',
            Godel='bind actual consumer/credit/visibility and contextual implementation',
            Ramanujan='compose placed CROM routes,16port deadlines and full graph after bounded providers'),
        jobs_launched=0,checkpoint_reads=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    with open(a.output,'w') as f:json.dump(build(),f,sort_keys=True,indent=2);f.write('\n')
