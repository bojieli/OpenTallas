"""Bind immutable warm mapping to topology and immediate priced slot failure."""
import argparse,hashlib,json,subprocess
from decimal import Decimal as D

def build():
    pins={}
    def load(n,ref,path):
        raw=subprocess.check_output(['git','show',ref+':'+path]);pins[n]=dict(commit=ref,path=path,sha256=hashlib.sha256(raw).hexdigest());return json.loads(raw)
    warm=load('warm_mapping','9bd2ccdf0','results/quality/w16_engram_initializer_20261001/warm_residency.json')
    cost=load('warm_product_price','952274ac5','results/uarch/w10_crom_warm_product_budget_r1/budget.json')
    fp=load('retained_SU_slot','541a1d2f','results/floorplan/v41_pack_refit_w10_interim.json')
    assert cost['source_mapping_digest']==warm['mapping_digest']
    assert cost['extra_persistent_product_FF_per_home']==655360
    assert cost['candidate_20entry_read_MUX2_bits_per_home']==622592
    region=next(r for r in fp['soft_regions'] if r[0]=='HUB_SU_VECTOR')
    slot=D(str(region[4]))*D(str(region[5]))/1000000
    core=D(str(fp['refit']['hub_units']['stream_unit']['area_mm2']))
    slack=slot-core;product=D(cost['per_affected_home']['conditional_cell_plus_macro_area_mm2'])
    assert product>slack
    return dict(schema='opentallas.CROM-warm-current-admission.v1',source_pins=pins,
        allocation_scope='candidate FF reservations, not current DUTcache; 164homes not accepted topology',
        core_SU_mm2_per_home=str(core),SU_slot_mm2=str(slot),available_after_core_mm2=str(slack),
        extra_product_per_home=cost['per_affected_home'],
        extra_product_alone_slot_deficit_mm2=str(product-slack),
        affected_reference_owners=cost['affected_reference_owners'],
        all8reference_owner_addition=cost['eight_reference_home_allocation_sum'],
        aggregate_is_not_phase_power=True,
        immediate_failures=['priced persistentEngramproduct alone exceeds retainedSUslot slack beforeothernewcache/control',
            'compactothercache requires uninstantiated bankread-to-lane delivery',
            'regularlane-localother17/19slots exceeds candidate4slots',
            'four sequentialrankSUs cannot retain all40layergamma withtwofamilyallocation',
            '164SUowners and1960.784mm2 core charge not accepted wholephysicaltopology',
            'L1invalid plus cold/reset/image/lease provider absent'],
        cold=dict(candidate_initialization_partials=warm['cold_init']['SS17_cold_candidates'],
            actual_TTFT=None,hidden_preload_credit=False),
        warm=dict(actual_RTLcache_provider=None,live_L0_L20_hit_credit=False,actual_cycles=None,
            logical_readonly_reuse_no_arithmetic_change=True,coldcost_not_automatically_per_token=True),
        control_tag_reset_lease_extra_state_and_power=None,
        ungated_clock_cost_retained=True,no_clock_gating_credit=True,
        actual_whole_power_W=None,actual_whole_margin_W=None,
        verdict='FAIL_CURRENT_WARM_RESIDENT_CONSTRUCTION_BEFORE_RTL',
        failure_is_priced_candidate_not_physical_minimum=True,
        selected_adopted_point=None,hardware_admission=False,jobs_launched=0,checkpoint_reads=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    with open(a.output,'w') as f:json.dump(build(),f,sort_keys=True,indent=2);f.write('\n')
