#!/usr/bin/env python3
"""Join finite hybrid leases to retained staging without resident-product costs."""
import argparse
from decimal import Decimal as D
import json
from pathlib import Path
from tools.w10_crom_control_reservation import read

def build(hybrid, typed):
    h = hybrid['hybrid']
    if (h['gamma_words_per_layer_home'], h['operand_words_per_layer_home'],
        h['persistent_other_slots'], h['single_streamed_product_slot']) != (10240,4096,[0,1,2],3):
        raise ValueError('unsupported slot roles')
    owners = hybrid['topology']['dense_cache_owners']
    keys = [(o['rank'],o['logical_layer']) for o in owners]
    if len(keys)!=160 or set(keys)!={(r,l) for r in range(4) for l in range(40)}:
        raise ValueError('dense owner mapping incomplete')
    hub = hybrid['area_bridge']['existing_PRODUCT_HUB']
    if D(str(hub['block_mm2'])) != D('38.601'):
        raise ValueError('hub allocation changed')
    rows=[]
    for r in typed['cases']:
        if r['FF_by_role']['retained_staging']!=475402:
            raise ValueError('retained staging no longer matches gamma and operand construction')
        c=next(c for c in hybrid['product_calendars'] if (c['banks'],c['credits'])==(r['parameter_banks'],r['credits']))
        if len(c['commands'])!=2 or any(len(cmd['events'])!=20 for cmd in c['commands']):
            raise ValueError('incomplete product calendar')
        for cmd in c['commands']:
            for event in cmd['events']:
                if event['slot']!=3 or event['candidate_owning_slot_reverse_credit_tick']<=event['read_capture_tick']:
                    raise ValueError('slot lease released before owning capture')
        cost=r['fresh_declared_reservation']
        rows.append({'parameter_banks':r['parameter_banks'],'catalog_banks':r['catalog_banks'],
            'credits':r['credits'],'FF_by_role':r['FF_by_role'],
            'retained_conservative_per_dense_home_reservation':cost,
            'dense160_allocation_sum':{k:str(D(cost[k])*160) for k in (
                'conditional_cell_plus_macro_area_mm2','ungated_clock_W','all_state_leakage_upper_W')},
            'source_product_calendar':c,
            'current_hub_increment_area_mm2':None,'current_hub_slot_fit':None,
            'physical_admission':False})
    return {'schema':'w10_crom_hybrid_source_budget_v1','cases':rows,
        'retained_gamma_FF_per_dense_home':327680,'operand_FF_per_dense_home_counted_once':131072,
        'persistent_product_FF':0,'persistent_product_read_MUX2_bits':0,
        'zero_resident_product_is_not_zero_ROM_service':True,
        'current_PRODUCT_HUB':hub,'existing164_hub_area_mm2':hybrid['area_bridge']['existing164_hub_reservation'],
        'retained_reservation_scope':'Fresh SS17 construction already charges gamma, two operand buffers, landing/raw capture/select/catalog/tag/credit/route and its CTS once. Conservative allocation; no transfer of historical SU slack or assumption that current hub absorbs it.',
        'dense_cache_owner_count':160,'field_stage40_dense_cache_words':0,
        'head_norm_service':hybrid['topology']['head'],
        'allocation_sum_is_not_phase_simultaneous_power':True,
        'historical_SU_slack_used':False,'buffer_reuse_savings_credit':0,
        'resident_product_failure_preserved':'952274ac5 and fe82442c9 reject the resident alternative only.',
        'actual_provider_instantiated':False,'additional_role_controller_bits':None,
        'actual128bit_CDC_extra_state_bits':None,'whole_power_W':None,
        'whole_margin_W':None,'actual_TTFT':None,'actual_warm_cycles':None,
        'root_stop_credit':0,'physical_admission':False,'jobs_launched':0,
        'missing':['slot-role controller/other-bank-to-lane permutation and capture ACK provider',
                   'current hub lane/VM area bridge and actual macro/cache/CTS/PG/route fit',
                   'actual1152bus reach and128CDC inventory/reset/drain',
                   'headnorm fanout, all-family initialization and operator deadlines',
                   'source L1 provenance, full phase power/IR/contextual SSFF'],
        'verdict':'HYBRID_PRODUCT_SERVICE_PRICED_NO_RESIDENT_ARRAY_OR_BUFFER_DOUBLE_CHARGE_NO_ADMISSION'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    h,hp=read('f1af146d6','results/quality/w16_engram_initializer_20261001/hybrid_topology.json')
    t,tp=read('db6ae8e09','results/uarch/w10_crom_ss_route17_budget_r1/budget.json')
    x=build(h,t);x['source_pins']={'hybrid':hp,'typed_SS17':tp}
    Path(a.output).write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')

if __name__=='__main__':main()
